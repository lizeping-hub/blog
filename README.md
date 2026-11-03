# 励泽坪 · 文章

Hugo + PaperMod 文章站，发布于 https://lizeping-hub.github.io/blog/ 。

## 本地预览

安装 Hugo **0.169.0 extended**，然后运行：

```sh
git clone --recurse-submodules https://github.com/lizeping-hub/blog.git
cd blog
hugo server
```

文章位于 `content/posts/<slug>/index.md`，图片与文章放在同一个文件夹。
主题以 Git 子模块固定到已验证版本，不自动升级。日常发文无需改主题文件。

## 发文与更新

添加或修改 Markdown 与图片后，推送到 `main`。GitHub Actions 会自动构建、检查并发布。
飞书改动不会自动同步到本站；需重新读取、转换、核对后提交。

首页、导航和全站设置在 `hugo.toml`；少量中文阅读样式在 `assets/css/extended/reading.css`。

## 首批飞书文章

首批三篇于 **2026-11-03** 收录；此日期是迁移日期，不代表原始写作日期。
正文、图文顺序、表格和代码内容按原文迁移，Mermaid 源码保留为代码块。
全文比对忽略排版空白字符，图片以 SHA-256 验证原文件一致。
原文链接、版本及图片校验值记录在 `content-manifest.json`。
没有明确授权给第三方使用文章和图片的许可；PaperMod 主题按其自身 MIT 许可使用。

构建后验证收录文章的资源和结构：

```sh
hugo --gc --minify
python3 scripts/verify_import.py
```

如需再次从已获取的飞书快照生成首批文章（快照留在本地，不提交 API 响应）：

```sh
python3 scripts/import_feishu.py /path/to/source-audit --imported-at YYYY-MM-DD
hugo --gc --minify
python3 scripts/verify_import.py /path/to/source-audit
```

`source-audit` 应包含三份 `article-N-latest.json` 完整读取响应，以及 `assets/article-N-I.*` 原图。
`import_feishu.py` 仅转换本地材料，不调用接口，也不会发布。
