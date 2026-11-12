# CodeAnalyse（CodeStat Rust/egui 版）项目记忆

## 技术要点
- 桌面框架：eframe/egui 0.36.2（glow 后端，关闭 wgpu/default 减少依赖），依赖全部来自本地 cargo 缓存，构建用 `cargo build --offline`。
- egui 0.36 关键 API：App 用 `ui(&mut self, &mut egui::Ui, frame)` + `logic`；面板用 `egui::Panel::left(...).exact_size(...)`；样式用 `ctx.all_styles_mut`；`TextEdit::frame(Frame::NONE)`；`Window::show(ctx,...)`/`Modal::show(ctx,...)` 仍用 Context。
- 中文字体：启动时从 `%WINDIR%/Fonts/msyh.ttc`（回退 Deng.ttf/simhei.ttf）加载，skrifa 支持 TTC；插入到 Proportional/Monospace 首位。UI 图标避免 [] / ∅ / ▤ 等缺字形符号，用汉字「文」「空」等。
- docx：自研轻量 OOXML 生成器（src/docx.rs），zip Stored 方式写入；Word 导出带前后各 60 页截断（LINES_PER_PAGE=37, FILE_OVERHEAD_LINES=7）。

## 项目约定（用户要求）
- 每次修改后立即提交 git，按逻辑批次，提交信息中文。
- 代码必须写好中文注释（模块头 + 公共 API + 关键逻辑）。
- 测试统一放在根目录 tests/（不用 src 内嵌 #[cfg(test)]），当前 4 个测试文件 16 个用例全通过。
- pycode/ 是 Flet 版参考实现，保持不动；Rust 版与其功能对齐（40+ 语言、.codestatignore、JSON/CSV/Word 导出、MD 转 Word）。

## 验证技巧
- UI 截图：Cargo.toml 临时加 eframe feature `__screenshot`，设 `EFRAME_SCREENSHOT_TO=<绝对路径>` 运行 exe，首帧自动保存 PNG 后退出；验证后记得移除该 feature。
