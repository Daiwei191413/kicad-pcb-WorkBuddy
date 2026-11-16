# KiCad PCB WorkBuddy 技能包

本仓库用于保存用户提供的 `kicad-pcb-codegen.zip` 技能包。压缩包内的 8 个文件已原样解压至仓库根目录，原始 ZIP 同时保留，便于浏览与下载。

## 内容

- [SKILL.md](SKILL.md)：技能入口与使用流程；包内技能名称保持为 `kicad-pcb-codegen`。
- [scripts/](scripts/)：PCB 文件处理、DRC 汇总和制造文件导出脚本。
- [assets/](assets/)：原理图与 PCB 代码生成模板。
- [references/](references/)：工作流与问题记录。
- [原始技能包 ZIP](kicad-pcb-codegen.zip)：上传前的原始压缩文件。

## 使用

将本仓库链接交给支持本地 Skills 的 AI Agent，要求先阅读 `SKILL.md`、核对 KiCad 和 Python 环境，再按该 Agent 的安装方式使用。若安装器支持自定义目录名，使用包内名称 `kicad-pcb-codegen`。

原包提及的 `kicad-schematic-codegen` 配套技能不在本仓库中。

## 上传范围

本次仅整理上传并核对文件完整性，未运行绘板、DRC 或制造导出流程。原包中关于 KiCad 版本、实例结果和设计规则的描述保留原文，未在本次上传中重新验证。

原始压缩包未附单独许可证文件；本仓库未额外添加许可证或改写作者归属。
