# 复现与证据分级

运行环境：Python 3.10+标准库；本次实际版本与OS见evidence/author_run_001/environment.json。脚本无Anki依赖、联网分类或pip安装。不要使用python -O运行校验脚本：校验用assert执行验证。`-B`避免生成缓存文件。

从解压包根运行：

```bash
python -B design/linguistic/verification/verify_source_inputs.py
python -B design/linguistic/verification/verify_delivery.py
python -B -m unittest discover -s design/linguistic/verification -p 'test_*.py' -v
python -B design/linguistic/verification/verify_manifest.py
python -B design/linguistic/verification/verify_delivery.py --formal
```

前四项目标退出0；最后一项必须输出BLOCKED并退出3，不能把“观察到预期阻塞”写成正式门禁PASS。当前包永远不能通过切换布尔值变成生产授权。

可将验证日志写入包外一个**尚不存在**的目录，避免覆盖原始证据和破坏清单：

```bash
python -B design/linguistic/verification/run_checks.py --output ../p09_recheck_001
```

运行记录保存命令、cwd、UTC时间、实际stdout/stderr、退出码及日志SHA。作者数据检查72条；单元测试包含输入边界、无发奖权限、覆写重放及合成旧版本回滚。分类数据检查与unittest中的同一fixtures是两种入口，不能相加声称144条独立案例。

JSON Schema文件已提供并做JSON语法/声明检查；本环境没有jsonschema安装元数据，未运行第三方Schema引擎；P22独立验证NOT_RUN。手写输入守卫验证只证明本参考实现行为。初始环境探查失败已保留setup_probe.json，随后采用标准库；该失败不是目标机或Anki测试。

证据范围：本岗作者SOURCE/STATIC/REFERENCE-UNIT检查。独立SPEC、P22 Schema、P32真实单元/正式契约、目标机、Anki E2E、P33人工以及P35分级门禁全部NOT_RUN；真实字段和正式接入前置为BLOCKED。没有学习账本、钱包或事务实际运行。
