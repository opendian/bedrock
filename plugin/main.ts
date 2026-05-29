import {
  App,
  FileSystemAdapter,
  MarkdownView,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
} from "obsidian";
import { execFile } from "child_process";
import * as fs from "fs";
import * as path from "path";

interface Segment {
  text: string;
  start: number;
  end: number;
}

interface CaptionPayload {
  wav: string;
  lang: string;
  segments: Segment[];
}

interface BedrockVoiceSettings {
  backend: string; // claude | codex | local
  lang: string; // en | fr
  voice: string;
  rate: number;
  whole: boolean;
  voicePath: string; // relative to vault root, or absolute. Empty = use bundled <plugin>/voice/.
}

const DEFAULTS: BedrockVoiceSettings = {
  backend: "claude",
  lang: "en",
  voice: "af_heart",
  rate: 1.0,
  whole: false,
  voicePath: "",
};

export default class BedrockVoice extends Plugin {
  settings: BedrockVoiceSettings;
  hud: CaptionHud | null = null;

  async onload() {
    await this.loadSettings();

    this.addRibbonIcon("audio-lines", "Read note aloud (Bedrock Voice)", () => this.readActive());
    this.addCommand({
      id: "read-note-aloud",
      name: "Read note aloud with captions",
      callback: () => this.readActive(),
    });
    this.addCommand({
      id: "stop-reading",
      name: "Stop reading",
      callback: () => this.stop(),
    });
    this.addSettingTab(new BedrockVoiceSettingTab(this.app, this));
  }

  onunload() {
    this.stop();
  }

  stop() {
    this.hud?.destroy();
    this.hud = null;
  }

  private vaultBase(): string {
    const adapter = this.app.vault.adapter;
    if (adapter instanceof FileSystemAdapter) return adapter.getBasePath();
    throw new Error("Bedrock Voice needs a desktop vault");
  }

  /** Resolve the voice pipeline directory. Default: <plugin folder>/voice/.
   *  User can override via the `voicePath` setting (vault-relative or absolute). */
  private resolveVoiceDir(): string {
    const setting = this.settings.voicePath?.trim();
    if (setting) {
      return path.isAbsolute(setting) ? setting : path.join(this.vaultBase(), setting);
    }
    const pluginDir = (this.manifest as { dir?: string }).dir;
    if (!pluginDir) throw new Error("Bedrock Voice: plugin folder unknown");
    return path.join(this.vaultBase(), pluginDir, "voice");
  }

  async readActive() {
    const view = this.app.workspace.getActiveViewOfType(MarkdownView);
    const file = view?.file ?? this.app.workspace.getActiveFile();
    if (!file) {
      new Notice("Bedrock Voice: no active note");
      return;
    }

    let voiceDir: string;
    try {
      voiceDir = this.resolveVoiceDir();
    } catch (e) {
      new Notice((e as Error).message, 8000);
      return;
    }

    const py = path.join(voiceDir, ".venv", "bin", "python");
    const script = path.join(voiceDir, "note_to_audio.py");
    if (!fs.existsSync(script)) {
      new Notice(
        `Bedrock Voice: pipeline missing at ${voiceDir}. Run install.sh from the README first.`,
        10000,
      );
      return;
    }
    if (!fs.existsSync(py)) {
      new Notice(
        "Bedrock Voice: Python venv missing. Run `bash install.sh` inside the voice/ folder.",
        10000,
      );
      return;
    }

    const base = this.vaultBase();
    const args = [script, path.join(base, file.path), "--captions", "--lang", this.settings.lang];
    if (this.settings.whole) args.push("--whole");

    const notice = new Notice(`Bedrock Voice: preparing audio (${this.settings.backend})…`, 0);
    try {
      const payload = await this.run(py, args, voiceDir);
      notice.hide();
      if (!payload.segments?.length) throw new Error("no captions returned");
      this.stop();
      const rel = path.relative(base, payload.wav).split(path.sep).join("/");
      const src = this.app.vault.adapter.getResourcePath(rel);
      this.hud = new CaptionHud(payload, src, this.settings.rate, () => (this.hud = null));
    } catch (e) {
      notice.hide();
      new Notice("Bedrock Voice: " + (e as Error).message, 8000);
    }
  }

  private run(py: string, args: string[], cwd: string): Promise<CaptionPayload> {
    const env = {
      ...process.env,
      BEDROCK_LLM_BACKEND: this.settings.backend,
      BEDROCK_KOKORO_VOICE: this.settings.voice,
      BEDROCK_KOKORO_LANG: this.settings.lang === "fr" ? "f" : "a",
    };
    return new Promise((resolve, reject) => {
      execFile(py, args, { cwd, env, maxBuffer: 32 * 1024 * 1024 }, (err, stdout, stderr) => {
        if (err) {
          const tail = (stderr || "").trim().split("\n").filter(Boolean).pop();
          return reject(new Error(tail || err.message));
        }
        // stdout may carry library warnings; find the JSON payload line, scanning from the end.
        const lines = stdout.split("\n").map((l) => l.trim()).filter(Boolean);
        for (let k = lines.length - 1; k >= 0; k--) {
          if (!lines[k].startsWith("{")) continue;
          try {
            return resolve(JSON.parse(lines[k]) as CaptionPayload);
          } catch {
            /* keep scanning */
          }
        }
        reject(new Error("no JSON payload from note_to_audio.py"));
      });
    });
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULTS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

/** Floating caption HUD with sentence + word-level karaoke synced to the audio. */
class CaptionHud {
  private el: HTMLElement;
  private audio: HTMLAudioElement;
  private curEl: HTMLElement;
  private nextEl: HTMLElement;
  private playBtn: HTMLButtonElement;
  private raf = 0;

  constructor(
    private payload: CaptionPayload,
    src: string,
    rate: number,
    private onClose: () => void,
  ) {
    this.el = document.body.createDiv({ cls: "bedrock-hud" });
    const stage = this.el.createDiv({ cls: "bedrock-stage" });
    this.curEl = stage.createDiv({ cls: "bedrock-cur" });
    this.nextEl = stage.createDiv({ cls: "bedrock-next" });

    const ctl = this.el.createDiv({ cls: "bedrock-ctl" });
    this.playBtn = ctl.createEl("button", { text: "⏸", cls: "bedrock-btn" });
    const speed = ctl.createEl("select", { cls: "bedrock-speed" });
    [0.75, 1, 1.25, 1.5, 1.75].forEach((v) => {
      const o = speed.createEl("option", { text: `${v}×`, value: String(v) });
      if (v === rate) o.selected = true;
    });
    const stopBtn = ctl.createEl("button", { text: "✕", cls: "bedrock-btn" });

    this.audio = new Audio(src);
    this.audio.playbackRate = rate;

    this.playBtn.onclick = () => this.toggle();
    stopBtn.onclick = () => this.destroy();
    speed.onchange = () => (this.audio.playbackRate = parseFloat(speed.value));
    this.audio.onended = () => this.destroy();

    this.keyHandler = this.keyHandler.bind(this);
    document.addEventListener("keydown", this.keyHandler);

    void this.audio.play();
    this.loop();
  }

  private keyHandler(e: KeyboardEvent) {
    if (e.key === "Escape") this.destroy();
    else if (e.key === " " && document.activeElement?.tagName !== "INPUT") {
      e.preventDefault();
      this.toggle();
    }
  }

  private toggle() {
    if (this.audio.paused) {
      void this.audio.play();
      this.playBtn.setText("⏸");
      this.loop();
    } else {
      this.audio.pause();
      this.playBtn.setText("▶");
    }
  }

  private loop() {
    this.render();
    if (!this.audio.paused && !this.audio.ended) {
      this.raf = requestAnimationFrame(() => this.loop());
    }
  }

  private render() {
    const t = this.audio.currentTime;
    const segs = this.payload.segments;
    let i = segs.findIndex((s) => t >= s.start && t < s.end);
    if (i < 0) i = t >= (segs[segs.length - 1]?.end ?? 0) ? segs.length - 1 : 0;
    const cur = segs[i];
    if (!cur) return;

    // word-level highlight: interpolate progress across the sentence by char count
    const dur = Math.max(0.001, cur.end - cur.start);
    const frac = Math.min(1, Math.max(0, (t - cur.start) / dur));
    const spokenChars = cur.text.length * frac;

    this.curEl.empty();
    let acc = 0;
    for (const token of cur.text.split(/(\s+)/)) {
      const span = this.curEl.createSpan({ text: token });
      if (acc + token.length <= spokenChars) span.addClass("spoken");
      else if (acc < spokenChars) span.addClass("speaking");
      acc += token.length;
    }
    this.nextEl.setText(segs[i + 1]?.text ?? "");
  }

  destroy() {
    cancelAnimationFrame(this.raf);
    document.removeEventListener("keydown", this.keyHandler);
    this.audio.pause();
    this.audio.removeAttribute("src");
    this.el.remove();
    this.onClose();
  }
}

class BedrockVoiceSettingTab extends PluginSettingTab {
  constructor(app: App, private plugin: BedrockVoice) {
    super(app, plugin);
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName("LLM backend")
      .setDesc(
        "How the spoken script is tightened. No metered API — uses CLI auth (your existing login) or local model.",
      )
      .addDropdown((d) =>
        d
          .addOptions({ claude: "claude CLI", codex: "codex CLI", local: "local (MLX-LM)" })
          .setValue(this.plugin.settings.backend)
          .onChange(async (v) => {
            this.plugin.settings.backend = v;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Narration language")
      .setDesc("EN rewrites the note for spoken cadence; FR keeps it French.")
      .addDropdown((d) =>
        d
          .addOptions({ en: "English", fr: "Français" })
          .setValue(this.plugin.settings.lang)
          .onChange(async (v) => {
            this.plugin.settings.lang = v;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Kokoro voice")
      .setDesc("e.g. af_heart, am_michael, bf_emma. FR voices use ff_/fm_ prefixes.")
      .addText((t) =>
        t.setValue(this.plugin.settings.voice).onChange(async (v) => {
          this.plugin.settings.voice = v.trim() || "af_heart";
          await this.plugin.saveSettings();
        }),
      );

    new Setting(containerEl)
      .setName("Default speed")
      .addSlider((s) =>
        s
          .setLimits(0.75, 1.75, 0.25)
          .setDynamicTooltip()
          .setValue(this.plugin.settings.rate)
          .onChange(async (v) => {
            this.plugin.settings.rate = v;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Read whole note")
      .setDesc("Off = `tldr` frontmatter + H2 headers only. On = the full body.")
      .addToggle((t) =>
        t.setValue(this.plugin.settings.whole).onChange(async (v) => {
          this.plugin.settings.whole = v;
          await this.plugin.saveSettings();
        }),
      );

    new Setting(containerEl)
      .setName("Voice pipeline path")
      .setDesc(
        "Where the Python pipeline lives. Leave empty to use the bundled `<plugin>/voice/`. Vault-relative or absolute path.",
      )
      .addText((t) =>
        t
          .setPlaceholder("(bundled)")
          .setValue(this.plugin.settings.voicePath)
          .onChange(async (v) => {
            this.plugin.settings.voicePath = v.trim();
            await this.plugin.saveSettings();
          }),
      );
  }
}
