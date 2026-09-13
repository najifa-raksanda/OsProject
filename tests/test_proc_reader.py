import os
import sys

import pytest

from exam_manager.proc_reader import read_process_detail


pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="/proc is Linux-specific")


def test_read_process_detail_for_current_process():
    detail = read_process_detail(os.getpid())
    assert detail is not None
    assert detail.pid == os.getpid()
    assert detail.vm_rss_kb > 0
    assert detail.voluntary_ctxt_switches >= 0
    assert detail.nonvoluntary_ctxt_switches >= 0
    assert detail.minor_faults >= 0
    assert detail.major_faults >= 0


def test_read_process_detail_returns_none_for_missing_pid():
    assert read_process_detail(999_999_999) is None