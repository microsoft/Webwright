(() => {
  const INTRO_HOLD_MS = 1250;
  const OUTRO_ANIMATION_MS = 820;
  const MAX_PLAYBACK_RATE = 5;

  const getNumber = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  };

  const getVideoDuration = (video) => {
    if (Number.isFinite(video.duration) && video.duration > 0) return video.duration;
    return getNumber(video.dataset.sourceDuration);
  };

  const applyTargetDuration = (video) => {
    const targetDuration = getNumber(video.dataset.targetDuration);
    const sourceDuration = getVideoDuration(video);
    if (!targetDuration || !sourceDuration || sourceDuration <= targetDuration) return;

    const rate = Math.min(MAX_PLAYBACK_RATE, sourceDuration / targetDuration);
    video.defaultPlaybackRate = rate;
    video.playbackRate = rate;
  };

  const createBumper = (logoSrc) => {
    const bumper = document.createElement("div");
    bumper.className = "video-bumper video-bumper--intro is-visible";
    bumper.setAttribute("aria-hidden", "true");

    const card = document.createElement("div");
    card.className = "video-bumper__card";

    const logo = document.createElement("img");
    logo.className = "video-bumper__logo";
    logo.src = logoSrc;
    logo.alt = "";

    card.append(logo);
    bumper.append(card);
    return bumper;
  };

  const setupVideoBumper = (wrap) => {
    if (wrap.dataset.bumperReady === "true") return;

    const video = wrap.querySelector("video");
    if (!video) return;

    wrap.dataset.bumperReady = "true";
    const bumper = createBumper(video.dataset.logoSrc || wrap.dataset.logoSrc || "./logo.png");
    wrap.appendChild(bumper);

    let introShown = false;
    let introTimer = 0;
    let outroTimer = 0;

    const setBumperMode = (mode) => {
      bumper.classList.toggle("video-bumper--intro", mode === "intro");
      bumper.classList.toggle("video-bumper--outro", mode === "outro");
    };

    const hideBumper = () => {
      bumper.classList.remove("is-visible");
      wrap.classList.remove("is-ending");
    };

    const clearTimers = () => {
      window.clearTimeout(introTimer);
      window.clearTimeout(outroTimer);
    };

    const showIntro = () => {
      if (introShown) return;
      clearTimers();
      introShown = true;
      setBumperMode("intro");
      bumper.classList.add("is-visible");
      introTimer = window.setTimeout(hideBumper, INTRO_HOLD_MS);
    };

    const showOutro = () => {
      clearTimers();
      introShown = false;
      setBumperMode("outro");
      wrap.classList.add("is-ending");
      outroTimer = window.setTimeout(() => {
        bumper.classList.add("is-visible");
      }, Math.round(OUTRO_ANIMATION_MS * 0.62));
    };

    video.addEventListener("loadedmetadata", () => applyTargetDuration(video));
    applyTargetDuration(video);

    video.addEventListener("play", () => {
      applyTargetDuration(video);
      if (video.currentTime < 0.35 && !introShown) {
        showIntro();
        return;
      }
      clearTimers();
      hideBumper();
    });

    video.addEventListener("ended", showOutro);
    video.addEventListener("seeking", () => {
      clearTimers();
      hideBumper();
    });
  };

  const setupAll = () => {
    document.querySelectorAll(".video-wrap").forEach(setupVideoBumper);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupAll);
  } else {
    setupAll();
  }
})();
