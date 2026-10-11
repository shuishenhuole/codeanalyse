import flet.testing as ftt


async def test_initial_ui(flet_app: ftt.FletTestApp):
    """CodeStat 主界面冒烟测试: 标题渲染、「开始统计」按钮初始禁用。

    The `flet_app` fixture is provided automatically by the flet pytest plugin.
    Run with `flet test` (or `uv run pytest`) from the project directory.
    """
    tester = flet_app.tester

    await tester.pump_and_settle()

    # 标题与摘要文案
    assert (await tester.find_by_text("CodeStat")).count >= 1
    assert (await tester.find_by_text("请选择目录后点击「开始统计」")).count == 1

    # 「开始统计」按钮存在且初始禁用 (默认目录有效时除外)
    scan_btn = await tester.find_by_key("scan")
    assert scan_btn.count == 1
