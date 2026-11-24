// Demo course renderer. Paywall rules (from the video):
// - Lesson text is public when publicContent is true, hidden otherwise.
// - Videos, slides, and attachments stay behind purchase, always.
async function main() {
  const res = await fetch("content.json");
  const data = await res.json();
  const section = document.getElementById("lessons");
  section.innerHTML = "";
  for (const lesson of data.course.lessons) {
    const article = document.createElement("article");
    const title = document.createElement("h2");
    title.textContent = lesson.title;
    article.appendChild(title);
    if (lesson.readingTimeMinutes) {
      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `About ${lesson.readingTimeMinutes} min read`;
      article.appendChild(meta);
    }
    if (lesson.publicContent) {
      const text = document.createElement("p");
      text.textContent = lesson.text;
      article.appendChild(text);
    } else {
      const locked = document.createElement("div");
      locked.className = "paywall";
      locked.textContent = "Lesson text is behind purchase. Buy the course to read it.";
      article.appendChild(locked);
    }
    const video = document.createElement("p");
    video.className = "meta";
    video.textContent = lesson.videoPaywalled
      ? "Video: locked (behind purchase)"
      : "Video: available";
    article.appendChild(video);
    section.appendChild(article);
  }
}

document.addEventListener("DOMContentLoaded", main);
