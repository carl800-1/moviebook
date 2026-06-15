# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions 自动构建发布流程
- 多平台打包支持（Linux、Windows、macOS）

### Changed
- 优化项目结构

## [1.0.2] - 2026-06-15

### Added
- ✨ 新增抖音平台支持，可采集抖音用户视频和评论
- ✨ 新增平台选择功能（B站 / 抖音 / 双平台）
- ✨ GUI 界面重新设计，支持多平台切换
- ✨ 配置文件自动保存功能

### Changed
- 🔧 优化电影名提取算法，提高准确率
- 🔧 改进 NAS Tool 连接检测机制

### Fixed
- 🐛 修复部分 B站 API 接口兼容性问题

## [1.0.1] - 2026-06-10

### Added
- ✨ 新增 GUI 图形界面
- ✨ 支持 B站 Cookie 登录
- ✨ 自动获取关注的 UP 主列表
- ✨ TMDB 电影名标准化
- ✨ NAS Tool 自动收藏功能
- 📝 新增演示脚本 demo.py

## [1.0.0] - 2026-06-01

### Added
- 🎉 项目初始化
- ✨ B站视频、评论、弹幕采集
- ✨ 正则表达式电影名提取
- ✨ NAS Tool API 对接