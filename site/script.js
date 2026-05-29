// Bedrock Voice landing — minimal interactivity.
// 1. Reveal-on-scroll for `.reveal` elements.
// 2. Pause hero video when off-screen (battery + a11y).

(function () {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Reveal on scroll
  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduced && revealEls.length) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target);
          }
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 },
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-in"));
  }

  // Pause hero video off-screen (saves battery, polite about autoplay)
  const heroVid = document.querySelector(".hero-demo video");
  if (heroVid && "IntersectionObserver" in window) {
    const vio = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            heroVid.play().catch(() => { /* autoplay blocked is fine */ });
          } else {
            heroVid.pause();
          }
        });
      },
      { threshold: 0.1 },
    );
    vio.observe(heroVid);
  }

  // Respect reduced motion: stop the hero logo float
  if (reduced) {
    const heroLogo = document.querySelector(".hero-logo");
    if (heroLogo) heroLogo.style.animation = "none";
  }
})();
