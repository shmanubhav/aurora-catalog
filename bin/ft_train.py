"""laya.train_cli with the fp32 calibration passes scored 2 articles at a time instead of 16.

Usage (in the laya-batch container): python -I ft_train.py [train_cli args...]
At max_len 4096 those passes run without autocast, and 16 long articles at once need more than the
7900 XTX's 24 GB for attention alone; the scores do not depend on the batch size.
"""
import functools
import os
import sys

os.environ.setdefault("PYTORCH_HIP_ALLOC_CONF", "expandable_segments:True")

import laya.train as train   # noqa: E402  (the allocator setting must precede the torch import)
from laya import train_cli   # noqa: E402

train.calibration_records = functools.partial(train.calibration_records, batch_size=2)
sys.exit(train_cli.main())
