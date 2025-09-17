const cells = Array.from(document.querySelectorAll(".cell"));
const statusEl = document.getElementById("status");
const resetBtn = document.getElementById("reset");
const modeSel = document.getElementById("mode");

let board, current, gameOver, mode;

// მოსაგები კომბინაციები
const wins = [
  [0,1,2],[3,4,5],[6,7,8], // rows
  [0,3,6],[1,4,7],[2,5,8], // cols
  [0,4,8],[2,4,6]          // diags
];

init();

resetBtn.addEventListener("click", init);
modeSel.addEventListener("change", () => {
  mode = modeSel.value;
  init();
});

cells.forEach(btn => btn.addEventListener("click", () => onMove(+btn.dataset.index)));

function init() {
  board = Array(9).fill("");
  current = "X";
  gameOver = false;
  mode = modeSel.value || "human";
  cells.forEach(c => {
    c.disabled = false;
    c.textContent = "";
    c.classList.remove("x","o");
  });
  setStatus(`სვლა: ${current}`);
}

function onMove(i) {
  if (gameOver || board[i] !== "") return;

  place(i, current);

  const result = evaluate(board);
  if (result) return end(result);

  // თუ AI რეჟიმია და ახლა ბოტის ჯერია
  if (mode === "ai" && current === "O" && !gameOver) {
    window.setTimeout(aiMove, 180); // პატარა პაუზა „ადამიანურობისთვის“
  }
}

function place(i, p) {
  board[i] = p;
  cells[i].textContent = p;
  cells[i].classList.add(p.toLowerCase());
  cells[i].disabled = true;

  // შემოწმება
  const result = evaluate(board);
  if (result) {
    end(result);
  } else {
    current = (p === "X") ? "O" : "X";
    setStatus(`სვლა: ${current}`);
  }
}

function setStatus(t) {
  statusEl.textContent = t;
}

// აბრუნებს: "X", "O", "draw" ან null
function evaluate(b) {
  for (const [a,b1,c] of wins) {
    if (b[a] && b[a] === b[b1] && b[a] === b[c]) return b[a];
  }
  if (b.every(v => v !== "")) return "draw";
  return null;
}

function end(result) {
  gameOver = true;
  cells.forEach(c => c.disabled = true);

  if (result === "draw") {
    setStatus("ფრე 🤝");
  } else {
    setStatus(`მოიგო: ${result} 🏆`);
  }
}

// --- AI (უნებლი) — მინიმაქსი ---
function aiMove() {
  // ბოტი თამაშობს O-ით
  const best = minimax(board, "O");
  place(best.index, "O");
}

function availableMoves(b) {
  const m = [];
  for (let i = 0; i < 9; i++) if (b[i] === "") m.push(i);
  return m;
}

function minimax(b, player) {
  const result = evaluate(b);
  if (result === "X") return { score: -10 };
  if (result === "O") return { score: 10 };
  if (result === "draw") return { score: 0 };

  const moves = [];

  for (const idx of availableMoves(b)) {
    const move = { index: idx };
    b[idx] = player;

    if (player === "O") {
      const r = minimax(b, "X");
      move.score = r.score;
    } else {
      const r = minimax(b, "O");
      move.score = r.score;
    }

    b[idx] = "";
    moves.push(move);
  }

  // აირჩევს საუკეთესო ქულას
  let bestMove, bestScore;
  if (player === "O") {
    bestScore = -Infinity;
    for (let i = 0; i < moves.length; i++) {
      if (moves[i].score > bestScore) {
        bestScore = moves[i].score;
        bestMove = i;
      }
    }
  } else {
    bestScore = Infinity;
    for (let i = 0; i < moves.length; i++) {
      if (moves[i].score < bestScore) {
        bestScore = moves[i].score;
        bestMove = i;
      }
    }
  }

  return moves[bestMove];
}
