"""全倉第一個 ``conftest.py``(KARST-090)。

放在這裡的東西只有一個資格:**每個測試檔都會用到,而各自抄一份就會飄開。**
現時只有兩件——寫入者名字,與一個臨時真庫。

**不造假定義庫。** 每個要庫的測試照舊起一個臨時 sqlite **真庫**,照舊經唯一入口
寫(D-020 第 4 條):版本鏈、寫入者簽章、同名同值即沿用舊版、運行編號查重——
這些正是要驗的東西,造一個假的出來就等於不驗。臨時庫住在 ``tmp_path``,
**一句都不會寫到倉裡那個 ``karst.sqlite``**。

假引擎住在 ``tests/doubles/``,不住這裡:替身要明寫才拿得到,不應該由夾具悄悄
塞給每個測試。

KARST-093 會再加幾個夾具(把直接打生產庫那批網頁測試接去臨時庫),位留在這裡。
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from karst.gateway import Gateway

#: 寫入者名字。唯一入口每寫一列都蓋一個簽章,而簽章要有名字;測試沒有人手輸入,
#: 所以在這裡給一個一看就知道是測試的預設。**測試自己設了就不覆蓋**——有些測試
#: 正是要驗「換一個寫入者會怎樣」。
DEFAULT_TEST_WRITER = "karst-tests"


@pytest.fixture()
def writer_name(monkeypatch: pytest.MonkeyPatch) -> str:
    """給這個測試一個固定的寫入者名,回傳它。

    **刻意不是 autouse**:設了它就換走全部簽章的署名,而有些測試正是要驗
    「換一個寫入者會怎樣」。要用就明寫,不要由夾具悄悄改全倉的行為。
    """
    monkeypatch.setenv("KARST_WRITER", DEFAULT_TEST_WRITER)
    return DEFAULT_TEST_WRITER


@pytest.fixture()
def gateway(tmp_path, writer_name) -> Iterator[Gateway]:
    """一個開在 ``tmp_path`` 的**真庫**唯一入口。用完自動關。"""
    with Gateway.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def store(gateway: Gateway):
    """上面那個真庫的定義庫。只讀定義時用它,寫入請經 ``gateway``。"""
    return gateway.store
