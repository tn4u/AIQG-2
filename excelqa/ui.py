"""Giao diện terminal (Rich). Tự tắt khi không có TTY / --no-ui / CI. In ra stderr."""
from __future__ import annotations
import os, sys


class NullUI:
    """Log thuần ra stderr; an toàn cho chạy tự động."""
    def start(self, total):
        print(f"[excelqa] {total} questions", file=sys.stderr)

    def update(self, info):
        toks = info.get("prompt_tokens", 0) + info.get("completion_tokens", 0)
        cost = info.get("cost_usd", 0.0)
        err = f" ERR: {info['error']}" if info.get("error") and not info.get("answer") else ""
        print(f"[excelqa] {info['id']} -> {info.get('answer', '')!r} "
              f"({info.get('seconds', 0):.1f}s, {toks} tok, ${cost:.4f}){err}", file=sys.stderr)

    def finish(self, summary):
        print("[excelqa] done: " + ", ".join(f"{k}={v}" for k, v in summary.items()), file=sys.stderr)

    def message(self, text):
        print(f"[excelqa] {text}", file=sys.stderr)


class RichUI(NullUI):
    def __init__(self):
        from rich.console import Console
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
        self.console = Console(stderr=True)
        self.progress = Progress(SpinnerColumn(), TextColumn("[bold]Excel QA"), BarColumn(),
                                 MofNCompleteColumn(), TimeElapsedColumn(), console=self.console)
        self.rows = []

    def start(self, total):
        self.console.rule("[bold cyan]Excel QA")
        self.progress.start()
        self.task = self.progress.add_task("run", total=total)

    def update(self, info):
        self.rows.append(info)
        self.progress.advance(self.task)

    def finish(self, summary):
        from rich.table import Table
        self.progress.stop()

        # Bảng kết quả chi tiết từng câu hỏi
        t = Table(title="Kết Quả Chi Tiết Từng Câu Hỏi", header_style="bold cyan", border_style="dim")
        t.add_column("id", style="bold", no_wrap=True)
        t.add_column("answer", style="white")
        t.add_column("mode", style="dim")
        t.add_column("tokens", justify="right")
        t.add_column("cost", justify="right")
        t.add_column("sec", justify="right")
        t.add_column("status")

        for r in self.rows:
            ok = bool(r.get("answer"))
            tokens = r.get("prompt_tokens", 0) + r.get("completion_tokens", 0)
            cost = r.get("cost_usd", 0.0)
            cost_str = f"${cost:.4f}"
            cost_styled = f"[red]{cost_str}[/]" if cost > 0.10 else f"[yellow]{cost_str}[/]"
            t.add_row(
                str(r["id"]),
                str(r.get("answer", ""))[:50],
                str(r.get("mode", "")),
                f"{tokens:,}" if tokens else "0",
                cost_styled,
                f"{r.get('seconds', 0):.1f}s",
                "[green]OK[/]" if ok else f"[red]FAIL {r.get('error', '')[:35]}[/]"
            )
        self.console.print(t)

        # Bảng tổng hợp đối chiếu với các giới hạn đề thi (Yêu cầu BTC)
        q_total = summary.get("questions", len(self.rows))
        q_ans = summary.get("answered", 0)
        tot_sec = summary.get("total_sec", 0.0)
        avg_sec = summary.get("avg_sec", 0.0)
        tot_cost = summary.get("total_cost_usd", 0.0)
        max_cost = summary.get("max_cost_usd", 0.0)
        tot_tok = summary.get("total_tokens", sum(r.get("prompt_tokens", 0) + r.get("completion_tokens", 0) for r in self.rows))
        avg_tok = summary.get("avg_tokens", round(tot_tok / max(1, q_total)))
        ram_mb = summary.get("peak_ram_mb", 0.0)

        cost_valid = "[green]✓ Hợp lệ (< $0.10/câu)[/]" if max_cost <= 0.10 else "[red]✗ VƯỢT TRẦN (> $0.10/câu)[/]"
        time_valid = "[green]✓ Hợp lệ (< 40 phút)[/]" if tot_sec <= 2400 else "[red]✗ VƯỢT TRẦN (> 40 phút)[/]"
        ram_valid = "[green]✓ Hợp lệ (< 1,024 MB)[/]" if ram_mb <= 1024 else "[red]✗ VƯỢT TRẦN (> 1 GB)[/]"

        st = Table(title="Tổng Hợp Chỉ Số Kiểm Thử (Đối Chiếu Quy Định BTC)", header_style="bold magenta", border_style="cyan")
        st.add_column("Tiêu chí đánh giá", style="bold white")
        st.add_column("Kết quả đạt được", style="cyan")
        st.add_column("Giới hạn quy định", style="dim")
        st.add_column("Tình trạng", justify="center")

        pct = (q_ans * 100) // max(1, q_total)
        st.add_row("Số câu hoàn thành", f"{q_ans}/{q_total} ({pct}%)", "Đủ 100% ID", "[green]✓[/]" if q_ans == q_total else "[yellow]![/]")
        st.add_row("Thời gian thực thi", f"{tot_sec:.1f}s (TB: {avg_sec:.2f}s/câu)", "≤ 40 phút (2,400s)", time_valid)
        st.add_row("Chi phí gọi LLM", f"Tổng ${tot_cost:.4f} (Max: ${max_cost:.4f}/câu)", "≤ $0.10 USD/câu", cost_valid)
        st.add_row("Token tiêu thụ", f"Tổng {tot_tok:,} (TB: {avg_tok:,} tok/câu)", "Tối ưu ngân sách", "[green]✓[/]")
        st.add_row("Bộ nhớ RAM (Peak)", f"{ram_mb:.1f} MB", "≤ 1,024 MB (1 GB)", ram_valid)

        self.console.print(st)


def make_ui(no_ui: bool = False):
    if no_ui or not sys.stderr.isatty() or os.getenv("NO_COLOR") or os.getenv("CI"):
        return NullUI()
    try:
        return RichUI()
    except Exception:
        return NullUI()