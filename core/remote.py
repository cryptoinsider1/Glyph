#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Optional

class RemoteStorage:
    def __init__(self, config: dict, logger=None):
        self.config = config
        self.logger = logger
        self.enabled = config.get("use_remote", False)

    def send_file(self, local_path: Path, remote_path: Optional[str] = None) -> bool:
        if not self.enabled:
            if self.logger:
                self.logger.info("Remote storage disabled, skipping")
            return False
        # TODO: реализовать отправку через rsync/ssh
        if self.logger:
            self.logger.warning("Remote storage not implemented yet")
        return False
