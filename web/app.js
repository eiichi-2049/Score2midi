/* Score→MIDI front-end */
const $ = (sel) => document.querySelector(sel);

const dropZone = $("#dropZone");
const fileInput = $("#fileInput");
const jobList = $("#jobList");
const modelBadge = $("#modelBadge");

const jobs = new Map();

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.error || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function fmtSize(n) {
  if (!n) return "0 B";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / 1024 / 1024).toFixed(1) + " MB";
}

function statusText(j) {
  if (j.status === "queued") return "排队中";
  if (j.status === "running") return "AI 识别中…";
  if (j.status === "done") return "完成 · 可下载 MIDI";
  if (j.status === "error") return "失败：" + (j.error || j.message || "");
  return j.message || j.status;
}

function renderJobs() {
  const list = [...jobs.values()].sort((a, b) => (a.created || 0) - (b.created || 0));
  if (!list.length) {
    jobList.innerHTML = '<li class="empty">还没有任务。拖入图片开始。</li>';
    return;
  }
  jobList.innerHTML = "";
  for (const j of list) {
    const li = document.createElement("li");
    li.className = "job";
    const statusClass = j.status || "";
    const thumb = j.image
      ? `<img class="job-thumb" src="/preview/${encodeURIComponent(j.image)}" alt="" />`
      : `<div class="job-thumb"></div>`;
    const actions = [];
    if (j.status === "done" && j.midi) {
      actions.push(
        `<a class="btn primary sm" href="/api/download/${encodeURIComponent(j.midi)}?type=midi" download>下载 MIDI</a>`
      );
    }
    if (j.status === "done" && j.musicxml) {
      actions.push(
        `<a class="btn ghost sm" href="/api/download/${encodeURIComponent(j.musicxml)}?type=musicxml" download>MusicXML</a>`
      );
    }
    li.innerHTML = `
      ${thumb}
      <div>
        <div class="job-name">${j.filename || j.image || ""}</div>
        <div class="job-status ${statusClass}">${statusText(j)}</div>
      </div>
      <div class="job-actions">${actions.join("")}</div>
    `;
    jobList.appendChild(li);
  }
}

function upsertJob(job) {
  jobs.set(job.id, job);
  renderJobs();
}

async function uploadFile(file) {
  const buf = await file.arrayBuffer();
  const res = await api("/api/upload", {
    method: "POST",
    headers: {
      "X-Filename": encodeURIComponent(file.name || "score.png"),
      "Content-Type": "application/octet-stream",
    },
    body: buf,
  });
  upsertJob({
    id: res.job_id,
    filename: res.filename,
    status: "queued",
    message: "排队中",
    image: res.filename,
    created: Date.now(),
  });
}

async function handleFiles(fileList) {
  const files = [...fileList].filter((f) => f.type.startsWith("image/") || /\.(png|jpe?g|bmp|webp|tiff?)$/i.test(f.name));
  if (!files.length) return;
  for (const f of files) {
    try {
      await uploadFile(f);
    } catch (e) {
      upsertJob({
        id: "err-" + Math.random().toString(16).slice(2),
        filename: f.name,
        status: "error",
        message: "上传失败",
        error: e.message,
        created: Date.now(),
      });
    }
  }
}

// Drag & drop
["dragenter", "dragover"].forEach((ev) => {
  dropZone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach((ev) => {
  dropZone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
  });
});
dropZone.addEventListener("drop", (e) => {
  handleFiles(e.dataTransfer.files);
});
dropZone.addEventListener("click", (e) => {
  if (e.target.closest("button, label, a")) return;
  fileInput.click();
});
$("#btnPick").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  handleFiles(fileInput.files);
  fileInput.value = "";
});

$("#btnClear").addEventListener("click", () => {
  for (const [id, j] of jobs) {
    if (j.status === "done" || j.status === "error") jobs.delete(id);
  }
  renderJobs();
});

// Models dialog
async function refreshModels() {
  try {
    const data = await api("/api/models");
    if (data.ready) {
      modelBadge.textContent = "模型已就绪";
      modelBadge.className = "badge ok";
    } else {
      modelBadge.textContent = "模型缺失";
      modelBadge.className = "badge warn";
    }
    const ul = $("#modelList");
    ul.innerHTML = (data.items || [])
      .map(
        (m) =>
          `<li><span>${m.name}<br><small style="color:#555">${m.file}</small></span>
           <span class="${m.ready ? "ok" : "miss"}">${m.ready ? "就绪 · " + m.size_mb + " MB" : "缺失"}</span></li>`
      )
      .join("");
    return data;
  } catch (e) {
    modelBadge.textContent = "服务未连接";
    modelBadge.className = "badge warn";
    return null;
  }
}

$("#btnModels").addEventListener("click", async () => {
  await refreshModels();
  $("#modelDialog").showModal();
});

// CLI dialog
const CLI_TEXT = `# 图形界面（推荐）
双击「启动可携带版.bat」

# 命令行 · 单张
homr_gui\\.venv\\Scripts\\python.exe img2midi.py "乐谱.png" --out-dir "输出"

# 命令行 · 整个文件夹
homr_gui\\.venv\\Scripts\\python.exe img2midi.py "乐谱图片" --out-dir "输出"

# 只要 MusicXML（homr 原生）
cd homr_gui
.venv\\Scripts\\python.exe -m homr.main "图片.png"

# 预下载/修复模型
homr_gui\\.venv\\Scripts\\python.exe download_models.py`;

$("#btnCli").addEventListener("click", () => {
  $("#cliText").textContent = CLI_TEXT;
  $("#cliDialog").showModal();
});
$("#btnCopyCli").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(CLI_TEXT);
  } catch (_) {}
});

// Poll jobs
async function poll() {
  try {
    const data = await api("/api/jobs");
    for (const j of data.jobs || []) upsertJob(j);
    if ($("#rootPath").textContent === "…") {
      const h = await api("/api/health");
      $("#rootPath").textContent = h.root || "";
      $("#cliHint").textContent = `python img2midi.py 图片.png --out-dir "${h.root || ""}\\输出"`;
    }
  } catch (_) {}
}

refreshModels();
poll();
setInterval(poll, 1200);
setInterval(refreshModels, 15000);
