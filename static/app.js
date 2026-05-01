const reward = document.querySelector(".reward");

if (reward) {
  const record = Number(reward.dataset.record || 0);
  const bursts = record % 100 === 0 ? 42 : record % 10 === 0 ? 22 : 10;

  for (let index = 0; index < bursts; index += 1) {
    const spark = document.createElement("span");
    spark.className = "spark";
    spark.style.setProperty("--x", `${Math.random() * 240 - 120}px`);
    spark.style.setProperty("--y", `${Math.random() * 160 - 80}px`);
    spark.style.setProperty("--delay", `${Math.random() * 0.45}s`);
    reward.appendChild(spark);
  }
}

document.querySelectorAll("input").forEach((input) => {
  input.addEventListener("input", () => {
    input.value = input.value.toUpperCase();
  });
});
