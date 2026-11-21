"use strict";

const presets = {
  repair: {
    pi: [[0, 0], [1, 1.4], [2, 0.2], [3, 1.5], [4, 0.4]],
    sigma: [[0, 0.1], [1.3, 3.6], [4, 0.45]],
    delta: 0.5,
  },
  deletion: {
    pi: [[0, 0], [1.3, 1.4], [2.7, 0.2], [4, 1.3]],
    sigma: [[0, 0.1], [1.3, 1.35], [2.1, 3.6], [2.7, 0.25], [4, 1.2]],
    delta: 0.35,
  },
  insertion: {
    pi: [[0, 0], [1, 1.4], [2, 0.1], [3, 1.5], [4, 0.3]],
    sigma: [[0, 0], [2, 0.15], [4, 0.3]],
    delta: 0.25,
  },
  close: {
    pi: [[0, 0], [1, 1.2], [2, 0.1], [3, 1.4], [4, 0.4]],
    sigma: [[0, 0.2], [1.05, 1.05], [2, 0.3], [3.05, 1.2], [4, 0.55]],
    delta: 0.35,
  },
};

const clone = (value) => JSON.parse(JSON.stringify(value));
let state = { ...clone(presets.repair), selectedCurve: "pi", results: null, dragging: null };
let animationTimer = null;
let walkthrough = { index: null, playing: false };

const $ = (selector) => document.querySelector(selector);
const plot = $("#curve-plot");
const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const finiteLabel = (value) => Number.isFinite(value) ? String(value) : "∞";

function ordinaryFrechet(pi, sigma) {
  const dp = Array.from({ length: pi.length }, () => Array(sigma.length).fill(Infinity));
  for (let i = 0; i < pi.length; i += 1) {
    for (let j = 0; j < sigma.length; j += 1) {
      let previous = 0;
      if (i === 0 && j > 0) previous = dp[i][j - 1];
      else if (j === 0 && i > 0) previous = dp[i - 1][j];
      else if (i > 0 && j > 0) previous = Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
      dp[i][j] = Math.max(distance(pi[i], sigma[j]), previous);
    }
  }
  return dp.at(-1).at(-1);
}

function circleFromTwo(a, b) {
  const center = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  return { center, radius: distance(center, a) };
}

function circleFromThree(a, b, c) {
  const determinant = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]));
  if (Math.abs(determinant) < 1e-12) return null;
  const a2 = a[0] ** 2 + a[1] ** 2;
  const b2 = b[0] ** 2 + b[1] ** 2;
  const c2 = c[0] ** 2 + c[1] ** 2;
  const center = [
    (a2 * (b[1] - c[1]) + b2 * (c[1] - a[1]) + c2 * (a[1] - b[1])) / determinant,
    (a2 * (c[0] - b[0]) + b2 * (a[0] - c[0]) + c2 * (b[0] - a[0])) / determinant,
  ];
  return { center, radius: distance(center, a) };
}

function minimumEnclosingBall(points) {
  const candidates = points.map((point) => ({ center: [...point], radius: 0 }));
  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) candidates.push(circleFromTwo(points[i], points[j]));
  }
  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) {
      for (let k = j + 1; k < points.length; k += 1) {
        const circle = circleFromThree(points[i], points[j], points[k]);
        if (circle) candidates.push(circle);
      }
    }
  }
  return candidates
    .filter((circle) => points.every((point) => distance(circle.center, point) <= circle.radius + 1e-9))
    .sort((a, b) => a.radius - b.radius)[0];
}

function computeMu(pi, delta) {
  const mu = Array(pi.length + 1).fill(0);
  let left = 1;
  for (let i = 1; i <= pi.length; i += 1) {
    while (minimumEnclosingBall(pi.slice(left - 1, i)).radius > delta + 1e-9) left += 1;
    mu[i] = left;
  }
  return mu;
}

function deletionDP(pi, sigma, delta) {
  const m = pi.length; const n = sigma.length;
  const table = Array.from({ length: m + 1 }, () => Array(n + 1).fill(Infinity));
  table[0][0] = 0;
  for (let j = 1; j <= n; j += 1) table[0][j] = 1 + table[0][j - 1];
  for (let i = 1; i <= m; i += 1) {
    for (let j = 1; j <= n; j += 1) {
      table[i][j] = distance(pi[i - 1], sigma[j - 1]) > delta
        ? 1 + table[i][j - 1]
        : Math.min(table[i][j - 1], table[i - 1][j], table[i - 1][j - 1]);
    }
  }
  return { value: table[m][n], table };
}

function insertionDP(pi, sigma, delta, combined) {
  const m = pi.length; const n = sigma.length; const mu = computeMu(pi, delta);
  const table = Array.from({ length: m + 1 }, () => Array(n + 1).fill(Infinity));
  table[0][0] = 0;
  if (combined) for (let j = 1; j <= n; j += 1) table[0][j] = j;
  for (let j = 0; j <= n; j += 1) {
    const deque = [];
    for (let i = 1; i <= m; i += 1) {
      const entry = [i - 1, table[i - 1][j]];
      while (deque.length && deque.at(-1)[1] >= entry[1]) deque.pop();
      deque.push(entry);
      while (deque.length && deque[0][0] < mu[i] - 1) deque.shift();
      const insert = 1 + deque[0][1];
      if (j === 0) table[i][j] = insert;
      else if (distance(pi[i - 1], sigma[j - 1]) > delta) {
        table[i][j] = combined ? Math.min(1 + table[i][j - 1], insert) : insert;
      } else {
        table[i][j] = Math.min(table[i][j - 1], table[i - 1][j], table[i - 1][j - 1], insert);
      }
    }
  }
  return { value: table[m][n], table, mu };
}

function computeAll() {
  if (!state.pi.length || !state.sigma.length) return;
  const delta = state.delta;
  state.results = {
    ordinary: ordinaryFrechet(state.pi, state.sigma),
    deletion: deletionDP(state.pi, state.sigma, delta),
    insertion: insertionDP(state.pi, state.sigma, delta, false),
    combined: insertionDP(state.pi, state.sigma, delta, true),
  };
  $("#ordinary-value").textContent = state.results.ordinary.toFixed(3);
  for (const kind of ["deletion", "insertion", "combined"]) {
    $(`#${kind}-result`).textContent = finiteLabel(state.results[kind].value);
  }
  renderDP();
}

function bounds() {
  const points = [...state.pi, ...state.sigma];
  const xs = points.map((p) => p[0]); const ys = points.map((p) => p[1]);
  let minX = Math.min(...xs); let maxX = Math.max(...xs); let minY = Math.min(...ys); let maxY = Math.max(...ys);
  if (maxX - minX < 1) { minX -= .5; maxX += .5; }
  if (maxY - minY < 1) { minY -= .5; maxY += .5; }
  const padX = (maxX - minX) * .14; const padY = (maxY - minY) * .18;
  return { minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY };
}

function mapPoint(point, box) {
  return [55 + (point[0] - box.minX) / (box.maxX - box.minX) * 625, 395 - (point[1] - box.minY) / (box.maxY - box.minY) * 345];
}

function unmapPoint(point, box) {
  return [box.minX + (point[0] - 55) / 625 * (box.maxX - box.minX), box.minY + (395 - point[1]) / 345 * (box.maxY - box.minY)];
}

function svgElement(name, attributes = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

function renderPlot() {
  plot.replaceChildren();
  if (!state.pi.length || !state.sigma.length) return;
  const box = bounds();
  for (let x = 55; x <= 680; x += 78.125) plot.append(svgElement("line", { x1: x, y1: 50, x2: x, y2: 395, stroke: "#dfe8ed", "stroke-width": 1 }));
  for (let y = 50; y <= 395; y += 57.5) plot.append(svgElement("line", { x1: 55, y1: y, x2: 680, y2: y, stroke: "#dfe8ed", "stroke-width": 1 }));
  const current = currentWalkthroughCell();
  if (current && current.i > 0 && current.kind !== "deletion") {
    const result = state.results[current.kind];
    const start = result.mu[current.i] - 1;
    const ball = minimumEnclosingBall(state.pi.slice(start, current.i));
    const center = mapPoint(ball.center, box);
    const radiusX = ball.radius / (box.maxX - box.minX) * 625;
    const radiusY = ball.radius / (box.maxY - box.minY) * 345;
    plot.append(svgElement("ellipse", {
      cx: center[0], cy: center[1], rx: radiusX, ry: radiusY,
      fill: "rgba(116,103,232,.10)", stroke: "#7467e8", "stroke-width": 3,
      "stroke-dasharray": "9 7", "pointer-events": "none",
    }));
    plot.append(svgElement("circle", { cx: center[0], cy: center[1], r: 7, fill: "#7467e8", stroke: "white", "stroke-width": 3, "pointer-events": "none" }));
  }
  if (current && current.i > 0 && current.j > 0) {
    const piPoint = mapPoint(state.pi[current.i - 1], box);
    const sigmaPoint = mapPoint(state.sigma[current.j - 1], box);
    const compatible = distance(state.pi[current.i - 1], state.sigma[current.j - 1]) <= state.delta;
    plot.append(svgElement("line", {
      x1: piPoint[0], y1: piPoint[1], x2: sigmaPoint[0], y2: sigmaPoint[1],
      stroke: compatible ? "#62a934" : "#d84e63", "stroke-width": 4,
      "stroke-dasharray": "8 6", "pointer-events": "none",
    }));
  }
  for (const [name, color] of [["pi", "#ff7a45"], ["sigma", "#24c7d9"]]) {
    const mapped = state[name].map((point) => mapPoint(point, box));
    plot.append(svgElement("polyline", { points: mapped.map((p) => p.join(",")).join(" "), fill: "none", stroke: color, "stroke-width": 5, "stroke-linecap": "round", "stroke-linejoin": "round" }));
    mapped.forEach((point, index) => {
      const group = svgElement("g", { "data-curve": name, "data-index": index, tabindex: 0, role: "button", "aria-label": `${name} point ${index + 1}` });
      const active = current && ((name === "pi" && index === current.i - 1) || (name === "sigma" && index === current.j - 1));
      if (active) group.append(svgElement("circle", { cx: point[0], cy: point[1], r: 18, fill: "rgba(185,231,105,.28)", stroke: "#7dad36", "stroke-width": 3 }));
      group.append(svgElement("circle", { cx: point[0], cy: point[1], r: 11, fill: "white", stroke: color, "stroke-width": 5 }));
      group.append(svgElement("text", { x: point[0], y: point[1] - 18, "text-anchor": "middle", fill: "#31485a", "font-size": 13, "font-weight": 800 }));
      group.lastChild.textContent = `${name === "pi" ? "π" : "σ"}${index + 1}`;
      plot.append(group);
    });
  }
  plot.dataset.bounds = JSON.stringify(box);
  $("#pi-count").textContent = `${state.pi.length} vertices`;
  $("#sigma-count").textContent = `${state.sigma.length} vertices`;
}

function pointerPosition(event) {
  const rect = plot.getBoundingClientRect();
  return [(event.clientX - rect.left) / rect.width * 720, (event.clientY - rect.top) / rect.height * 440];
}

plot.addEventListener("pointerdown", (event) => {
  const group = event.target.closest("g[data-curve]");
  if (group) {
    state.dragging = { curve: group.dataset.curve, index: Number(group.dataset.index) };
    plot.setPointerCapture(event.pointerId);
    return;
  }
  const point = unmapPoint(pointerPosition(event), JSON.parse(plot.dataset.bounds));
  state[state.selectedCurve].push(point);
  walkthrough.index = null;
  $("#preset").value = "free";
  computeAll();
});

plot.addEventListener("pointermove", (event) => {
  if (!state.dragging) return;
  state[state.dragging.curve][state.dragging.index] = unmapPoint(pointerPosition(event), JSON.parse(plot.dataset.bounds));
  $("#preset").value = "free";
  computeAll();
});
plot.addEventListener("pointerup", () => { state.dragging = null; });
plot.addEventListener("pointercancel", () => { state.dragging = null; });

document.querySelectorAll(".segment").forEach((button) => button.addEventListener("click", () => {
  state.selectedCurve = button.dataset.curve;
  document.querySelectorAll(".segment").forEach((item) => item.classList.toggle("active", item === button));
  $("#plot-help").textContent = `Selected: ${state.selectedCurve === "pi" ? "reference curve π" : "editable curve σ"}. Drag vertices or click the plot.`;
}));

$("#delete-last").addEventListener("click", () => {
  if (state[state.selectedCurve].length > 1) state[state.selectedCurve].pop();
  walkthrough.index = null;
  $("#preset").value = "free"; computeAll();
});

function loadPreset(name) {
  if (name === "free") return;
  const selectedCurve = state.selectedCurve;
  state = { ...clone(presets[name]), selectedCurve, results: null, dragging: null };
  walkthrough.index = null;
  $("#delta").value = state.delta;
  $("#delta-output").textContent = state.delta.toFixed(2);
  computeAll();
}

$("#preset").addEventListener("change", (event) => loadPreset(event.target.value));
$("#reset").addEventListener("click", () => loadPreset($("#preset").value === "free" ? "repair" : $("#preset").value));
$("#run").addEventListener("click", computeAll);
$("#delta").addEventListener("input", (event) => {
  state.delta = Number(event.target.value); $("#delta-output").textContent = state.delta.toFixed(2); computeAll();
});
$("#dp-select").addEventListener("change", () => {
  walkthrough.index = null;
  renderDP(true);
});

function heatColor(value, max) {
  if (!Number.isFinite(value)) return "#eff3f6";
  const ratio = max === 0 ? 0 : value / max;
  return `hsl(${190 + ratio * 65} 72% ${92 - ratio * 24}%)`;
}

function stepOrder() {
  if (!state.results) return [];
  const kind = $("#dp-select").value;
  const table = state.results[kind].table;
  const order = [];
  for (let j = 0; j < table[0].length; j += 1) {
    for (let i = 0; i < table.length; i += 1) order.push({ kind, i, j });
  }
  return order;
}

function currentWalkthroughCell() {
  const order = stepOrder();
  if (!order.length || walkthrough.index === null) return null;
  return order[Math.max(0, Math.min(walkthrough.index, order.length - 1))];
}

function insertionChoice(result, i, j) {
  const start = result.mu[i] - 1;
  let minimum = Infinity;
  for (let row = start; row < i; row += 1) minimum = Math.min(minimum, result.table[row][j]);
  return 1 + minimum;
}

function explainStep(kind, i, j) {
  const result = state.results[kind];
  const table = result.table;
  const value = table[i][j];
  const candidates = [];
  let title = `State (${i}, ${j}) = ${finiteLabel(value)}`;
  let summary = "The empty prefixes need zero edits.";
  let pill = "Base case";
  let pillClass = "";
  const add = (label, candidateValue) => candidates.push({ label, value: candidateValue });

  if (i === 0 && j === 0) {
    add("empty π ↔ empty σ", 0);
  } else if (i === 0) {
    if (kind === "insertion") {
      summary = "Insertion cannot remove an original σ vertex, so a nonempty σ prefix cannot match an empty π prefix.";
      pill = "Impossible boundary"; pillClass = "far";
      add("deletion is forbidden", Infinity);
    } else {
      summary = `π is empty, so σ${j} must be deleted. Each boundary step adds one edit.`;
      pill = "Delete boundary"; pillClass = "far";
      add(`1 + ${kind === "deletion" ? "D" : "B"}[0,${j - 1}]`, 1 + table[0][j - 1]);
    }
  } else if (j === 0) {
    if (kind === "deletion") {
      summary = "Deleting from an empty σ cannot create a curve, so this state is infeasible.";
      pill = "Impossible boundary"; pillClass = "far";
      add("no σ vertex remains", Infinity);
    } else {
      const inserted = insertionChoice(result, i, j);
      summary = `σ is empty. Insert one center covering a valid suffix π${result.mu[i]}…π${i}.`;
      pill = "Insert boundary";
      add(`insert center for π${result.mu[i]}…π${i}`, inserted);
    }
  } else {
    const pairDistance = distance(state.pi[i - 1], state.sigma[j - 1]);
    const near = pairDistance <= state.delta;
    pill = near ? "Compatible pair" : "Pair too far";
    pillClass = near ? "" : "far";
    if (near) {
      summary = `Distance ${pairDistance.toFixed(3)} ≤ δ ${state.delta.toFixed(2)}. No edit is forced, so compare every legal predecessor.`;
      add(`keep σ${j} (from left)`, table[i][j - 1]);
      add(`reuse σ${j} (from above)`, table[i - 1][j]);
      add(`match π${i} ↔ σ${j} (diagonal)`, table[i - 1][j - 1]);
      if (kind !== "deletion") add(`insert center for π${result.mu[i]}…π${i}`, insertionChoice(result, i, j));
    } else if (kind === "deletion") {
      summary = `Distance ${pairDistance.toFixed(3)} > δ ${state.delta.toFixed(2)}. The only legal repair is deleting σ${j}.`;
      add(`delete σ${j}: 1 + D[${i},${j - 1}]`, 1 + table[i][j - 1]);
    } else if (kind === "insertion") {
      summary = `Distance ${pairDistance.toFixed(3)} > δ ${state.delta.toFixed(2)}. Deletion is forbidden, so insert a center for a valid π suffix.`;
      add(`insert center for π${result.mu[i]}…π${i}`, insertionChoice(result, i, j));
    } else {
      summary = `Distance ${pairDistance.toFixed(3)} > δ ${state.delta.toFixed(2)}. Compare deleting σ${j} with inserting a new center.`;
      add(`delete σ${j}: 1 + B[${i},${j - 1}]`, 1 + table[i][j - 1]);
      add(`insert center for π${result.mu[i]}…π${i}`, insertionChoice(result, i, j));
    }
  }
  return { title, summary, pill, pillClass, candidates, value };
}

function renderInspector(cell) {
  const detail = explainStep(cell.kind, cell.i, cell.j);
  const candidateHtml = detail.candidates.map((candidate) => {
    const winner = candidate.value === detail.value;
    return `<div class="candidate${winner ? " winner" : ""}"><span>${candidate.label}</span><span class="candidate-value">${finiteLabel(candidate.value)}</span></div>`;
  }).join("");
  $("#cell-inspector").innerHTML = `
    <p class="eyebrow">Current decision</p>
    <span class="decision-pill ${detail.pillClass}">${detail.pill}</span>
    <h4>${detail.title}</h4>
    <p>${detail.summary}</p>
    <div class="candidate-list">${candidateHtml}</div>`;
}

function stopPlayback() {
  clearInterval(animationTimer);
  walkthrough.playing = false;
  $("#step-play").textContent = "Play walkthrough";
}

function showStep(index, scroll = false) {
  const order = stepOrder();
  if (!order.length) return;
  walkthrough.index = Math.max(0, Math.min(index, order.length - 1));
  const cell = order[walkthrough.index];
  document.querySelectorAll(".dp-cell").forEach((button) => {
    const buttonOrder = Number(button.dataset.order);
    const revealed = buttonOrder <= walkthrough.index;
    button.classList.toggle("future", !revealed);
    button.classList.toggle("current", buttonOrder === walkthrough.index);
    button.textContent = revealed ? button.dataset.value : "·";
  });
  $("#step-counter").textContent = `State ${walkthrough.index + 1} of ${order.length} · column-major order`;
  $("#step-progress-fill").style.width = `${(walkthrough.index + 1) / order.length * 100}%`;
  $("#step-prev").disabled = walkthrough.index === 0;
  $("#step-next").disabled = walkthrough.index === order.length - 1;
  renderInspector(cell);
  renderPlot();
  if (scroll) document.querySelector(`.dp-cell[data-order="${walkthrough.index}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function renderDP(resetToEnd = false) {
  if (!state.results) return;
  stopPlayback();
  const kind = $("#dp-select").value; const result = state.results[kind];
  const titles = { deletion: "Deletion-only DP", insertion: "Insertion-only DP", combined: "Combined edit DP" };
  $("#dp-title").textContent = titles[kind];
  const order = stepOrder();
  const orderIndex = new Map(order.map((cell, index) => [`${cell.i},${cell.j}`, index]));
  const table = $("#dp-table"); table.replaceChildren();
  const max = Math.max(1, ...result.table.flat().filter(Number.isFinite));
  const header = document.createElement("tr"); header.append(document.createElement("th"));
  result.table[0].forEach((_, j) => { const th = document.createElement("th"); th.textContent = j === 0 ? "∅" : `σ${j}`; header.append(th); });
  table.append(header);
  result.table.forEach((row, i) => {
    const tr = document.createElement("tr"); const th = document.createElement("th"); th.textContent = i === 0 ? "∅" : `π${i}`; tr.append(th);
    row.forEach((value, j) => {
      const td = document.createElement("td"); const button = document.createElement("button");
      button.className = `dp-cell${Number.isFinite(value) ? "" : " infinity"}`;
      button.textContent = finiteLabel(value); button.dataset.value = finiteLabel(value);
      button.style.background = heatColor(value, max); button.dataset.i = i; button.dataset.j = j;
      button.dataset.order = orderIndex.get(`${i},${j}`);
      button.addEventListener("click", () => { stopPlayback(); showStep(Number(button.dataset.order), true); });
      td.append(button); tr.append(td);
    });
    table.append(tr);
  });
  if (resetToEnd || walkthrough.index === null || walkthrough.index >= order.length) walkthrough.index = order.length - 1;
  showStep(walkthrough.index);
}

$("#step-restart").addEventListener("click", () => { stopPlayback(); showStep(0, true); });
$("#step-prev").addEventListener("click", () => { stopPlayback(); showStep(walkthrough.index - 1, true); });
$("#step-next").addEventListener("click", () => { stopPlayback(); showStep(walkthrough.index + 1, true); });
$("#step-play").addEventListener("click", () => {
  if (walkthrough.playing) { stopPlayback(); return; }
  const order = stepOrder();
  if (walkthrough.index >= order.length - 1) showStep(0, true);
  walkthrough.playing = true;
  $("#step-play").textContent = "Pause";
  animationTimer = setInterval(() => {
    if (walkthrough.index >= order.length - 1) { stopPlayback(); return; }
    showStep(walkthrough.index + 1, true);
  }, 750);
});

computeAll();

