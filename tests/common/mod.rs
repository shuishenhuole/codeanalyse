//! 测试公共工具：临时目录封装
//!
//! 仅用于 `tests/` 下的集成测试。目录名带进程号与时间戳，
//! `Drop` 时自动清理，避免污染系统临时目录。

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

pub struct TempDir(PathBuf);

impl TempDir {
    /// 创建唯一临时目录
    pub fn new(tag: &str) -> Self {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        let path = std::env::temp_dir().join(format!(
            "codestat-test-{tag}-{}-{nanos}",
            std::process::id()
        ));
        std::fs::create_dir_all(&path).expect("创建临时目录");
        Self(path)
    }

    pub fn path(&self) -> &Path {
        &self.0
    }

    /// 写入文本文件，自动创建父目录
    pub fn write(&self, rel: &str, content: &str) {
        self.write_bytes(rel, content.as_bytes());
    }

    /// 写入二进制文件（用于测试图片）
    pub fn write_bytes(&self, rel: &str, content: &[u8]) {
        let path = self.0.join(rel);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).expect("创建子目录");
        }
        std::fs::write(path, content).expect("写入测试文件");
    }

    pub fn join(&self, rel: &str) -> PathBuf {
        self.0.join(rel)
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
