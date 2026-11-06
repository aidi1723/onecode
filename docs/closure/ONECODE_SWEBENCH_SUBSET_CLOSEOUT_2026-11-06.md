# SWE-bench 子集收尾，2026-11-06

版本保持 1.1.0。没有新增卦象。`IchingKernel.classify_outcome` 没有改。`claims_mainstream_parity` 保持 `false`。内核依赖保持 `dependencies = []`。这份记录不包含模型密钥。

测量代码停在 `834abbb`。本说明只记录已经核对过的 n100 运行，不改内核。

这是 `benchmarks/swebench-lite/subset.jsonl` 里 5 道题的本地记录。它不是 SWE-bench Docker 榜单，也不是 Harbor 分数。官方测试补丁留在 `benchmarks/swebench-lite/official/`，评分时才读入，不写进模型提示词。

## 已跑完的两题

模型都是 `deepseek-v4.1-flash`，通道是 `https://happycoding.xyz/v1`，流式返回。终端预算 15 轮。预测文件在 n100 的 `/tmp/swebench_eval/`，不在本仓库。

| 实例 | 会话 | 用时 | 补丁 | 本地评分 |
| --- | --- | --- | --- | --- |
| `django__django-11099` | `completed`，第 9 轮 `finish` | 499.47 秒 | 901 字节，两个用户名校验器改为 `r'\A[\w.@+-]+\Z'` | `before=1`，`after=0`，`resolved` |
| `sympy__sympy-20590` | `completed`，第 10 轮 `finish` | 1467.44 秒 | 476 字节，`Printable` 增加 `__slots__ = ()` | 容器内 `before=1`，`after=0` |

Django 预测账本里的 `outcome_status_code` 和 `iching_status_code` 都是 63。在这套内核里，63 是乾为天（`111111`）。

### Django

账本是 `/tmp/swebench_eval/predictions_deepseek_py312.jsonl`，一行。镜像是 n100 上的 `onecode-swebench:py312`（Python 3.12，含 `setuptools`、`pytz`、`sqlparse`）。

第 2 轮只改了 `ASCIIUsernameValidator`。第 3 轮容器里的 `tests/runtests.py --parallel=1` 退出码 0，这是基线仓库里的 3 个检查。第 4 轮只读复现看到 `UnicodeUsernameValidator` 仍接受尾随换行。第 6 轮补上 Unicode。第 8 轮再次跑官方命令，退出码 0。第 9 轮 `finish`。全程没有 `preset_test_immutable`。

`before=1` 到 `after=0` 来自事后套上的官方测试补丁。循环里那 3 个测试通过，不包含该补丁里的尾随换行断言。

### SymPy

账本是 `/tmp/swebench_eval/predictions_sympy_20590.jsonl`，一行。镜像是 n100 上的 `onecode-swebench:sympy`（Python 3.9.25，`mpmath` 1.4.1）。

第 7 轮把 `__slots__ = ()` 写进 `sympy/core/_print_helpers.py`。第 8 轮只读检查看到 `Symbol` 没有 `__dict__`。第 9 轮 `python bin/test test_immutable` 跑过矩阵和张量里同名的 28 个测试，退出码 0。第 10 轮 `finish`。

官方失败用例在 `sympy/core/tests/test_basic.py` 的 `test_immutable`。容器评分在基线 `cffd4e0` 上先打测试补丁：退出码 1，22 通过、1 失败，失败点是 `assert not hasattr(b1, '__dict__')`。再打模型补丁后退出码 0。这次评分是运行脚本里的容器检查，早于 `834abbb` 的 `evaluate_model_patch` 容器参数。

## 五份测试补丁

`git apply --check` 在各自基线提交上退出码都是 0。边车只含测试路径。

| 实例 | 基线 | 测试文件 |
| --- | --- | --- |
| `django__django-11099` | `d26b242` | `tests/auth_tests/test_validators.py` |
| `pytest-dev__pytest-5692` | `29e336bd9` | `testing/test_junitxml.py` |
| `sphinx-doc__sphinx-10325` | `7bdc11e87` | `tests/test_ext_autodoc_automodule.py`，`tests/roots/test-ext-autodoc/target/inheritance.py` |
| `astropy__astropy-12907` | `d16bfe05a` | `astropy/modeling/tests/test_separable.py` |
| `sympy__sympy-20590` | `cffd4e0f86` | `sympy/core/tests/test_basic.py` |

pytest、Sphinx、Astropy 能打上测试补丁，还没有各自的运行镜像，也没有模型运行。

## 镜像路由

求解时的默认镜像：

- `django/django`：环境变量为空，或残留 `onecode-swebench:sympy` 时，用 `onecode-swebench:py312`。
- `sympy/sympy`：环境变量为空，或残留 `onecode-swebench:py312` 时，用 `onecode-swebench:sympy`。
- 其他仓库：环境里如果是这两张镜像之一，调用前拿掉。

`834abbb` 让 `evaluate_model_patch` 在指定镜像里跑测试。Django 评分用 `onecode-swebench:py312`，SymPy 评分用 `onecode-swebench:sympy`。这条路径把工作区挂进镜像并设置 `PYTHONDONTWRITEBYTECODE=1`。它不用求解沙箱的只读根目录、断网和去掉全部 capabilities。

## 仍在本阶段之外

- 没有 SWE-bench 官方 Docker 全量分数。
- `claims_mainstream_parity` 保持 `false`。
- pytest、Sphinx、Astropy 的解释器和依赖镜像还没有做。
- 临时密钥文件不在仓库里，也不在 n100 的 `/tmp/onecode_happycoding_key`。
