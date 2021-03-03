# -*- coding: utf-8 -*-
# Copyright (c) 2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Configuration module."""

from copy import deepcopy
from typing import Any, Dict, List, Optional

import ruamel.yaml as yaml

from lpot.ux.utils.exceptions import ClientErrorException
from lpot.ux.utils.json_serializer import JsonSerializer
from lpot.ux.utils.logger import log
from lpot.ux.utils.workload.dataloader import Transform
from lpot.ux.utils.workload.evaluation import Evaluation
from lpot.ux.utils.workload.model import Model
from lpot.ux.utils.workload.pruning import Pruning
from lpot.ux.utils.workload.quantization import Quantization
from lpot.ux.utils.workload.tuning import Tuning


class Config(JsonSerializer):
    """Configuration class."""

    def __init__(self, data: Dict[str, Any] = {}):
        """Initialize Configuration class."""
        super().__init__()
        self._skip.append("model_path")
        self.model_path: str = data.get("model_path", "")
        self.model: Model = Model()
        self.domain: Optional[str] = data.get("domain", None)
        self.device: Optional[str] = None
        self.quantization: Optional[Quantization] = None
        self.tuning: Tuning = Tuning()
        self.evaluation: Optional[Evaluation] = None
        self.pruning: Optional[Pruning] = None

        self.initialize(data)

    def initialize(self, data: Dict[str, Any] = {}) -> None:
        """Initialize config from dict."""
        if isinstance(data.get("model"), dict):
            self.model = Model(data.get("model", {}))

        # [Optional] One of "cpu", "gpu"; default cpu
        self.device = data.get("device", None)

        if isinstance(data.get("quantization"), dict):
            self.quantization = Quantization(data.get("quantization", {}))

        if isinstance(data.get("tuning"), dict):
            self.tuning = Tuning(data.get("tuning", {}))

        if isinstance(data.get("evaluation"), dict):
            self.evaluation = Evaluation(data.get("evaluation", {}))

        if isinstance(data.get("pruning"), dict):
            self.pruning = Pruning(data.get("pruning", {}))

    def remove_dataloader(self) -> None:
        """Remove datalader."""
        if (
            self.evaluation
            and self.evaluation.accuracy
            and self.evaluation.accuracy.dataloader
        ):
            self.evaluation.accuracy.dataloader = None
        if (
            self.evaluation
            and self.evaluation.performance
            and self.evaluation.performance.dataloader
        ):
            self.evaluation.performance.dataloader = None
        if (
            self.quantization
            and self.quantization.calibration
            and self.quantization.calibration.dataloader
        ):
            self.quantization.calibration.dataloader = None

    def remove_accuracy_metric(self) -> None:
        """Remove accuracy metric in config."""
        if (
            self.evaluation
            and self.evaluation.accuracy
            and self.evaluation.accuracy.metric
        ):
            self.evaluation.accuracy.metric = None
            self.evaluation.accuracy = None

    def set_evaluation_dataloader(self, dataloader: dict) -> None:
        """Udpate dataloader in evaluation config."""
        dataset = {
            dataloader.get("name", "Unknown"): dataloader.get("params", {}),
        }
        if (
            self.evaluation
            and self.evaluation.accuracy
            and self.evaluation.accuracy.dataloader
        ):
            self.evaluation.accuracy.dataloader.set_dataset(deepcopy(dataset))
        else:
            log.warning("Could not set accuracy dataloader.")

        if (
            self.evaluation
            and self.evaluation.performance
            and self.evaluation.performance.dataloader
        ):
            self.evaluation.performance.dataloader.set_dataset(deepcopy(dataset))
        else:
            log.warning("Could not set performance dataloader.")

    def set_evaluation_dataset_path(self, dataset_path: str) -> None:
        """Update dataset path in evaluation config."""
        if dataset_path == "no_dataset_location":
            return
        if (
            self.evaluation
            and self.evaluation.accuracy
            and self.evaluation.accuracy.dataloader
            and self.evaluation.accuracy.dataloader.dataset
        ):
            self.evaluation.accuracy.dataloader.dataset.params.update(
                {"root": dataset_path},
            )
        else:
            log.warning("Could not set accuracy dataset path.")
        if (
            self.evaluation
            and self.evaluation.performance
            and self.evaluation.performance.dataloader
            and self.evaluation.performance.dataloader.dataset
        ):
            self.evaluation.performance.dataloader.dataset.params.update(
                {"root": dataset_path},
            )
        else:
            log.warning("Could not set performance dataset path.")

    def set_quantization_dataloader(self, dataloader: dict) -> None:
        """Udpate dataloader in quantization config."""
        if (
            self.quantization
            and self.quantization.calibration
            and self.quantization.calibration.dataloader
        ):
            calib_dataloader = {
                dataloader.get("name", "Unknown"): dataloader.get("params", {}),
            }
            self.quantization.calibration.dataloader.set_dataset(calib_dataloader)
        else:
            log.warning("Could not set performance dataloader.")

    def set_quantization_dataset_path(self, dataset_path: str) -> None:
        """Update dataset path in quantization config."""
        if dataset_path == "no_dataset_location":
            return
        if (
            self.quantization
            and self.quantization.calibration
            and self.quantization.calibration.dataloader
            and self.quantization.calibration.dataloader.dataset
        ):
            self.quantization.calibration.dataloader.dataset.params.update(
                {"root": dataset_path},
            )
        else:
            log.warning("Could not set quantization dataset path.")

    def set_workspace(self, path: str) -> None:
        """Update tuning workspace path in config."""
        if self.tuning is None:
            raise Exception("Tuning section not defined!")
        self.tuning.workspace.path = path

    def set_accuracy_goal(self, accuracy_goal: float) -> None:
        """Update accuracy goal in config."""
        try:
            accuracy_goal = float(accuracy_goal)
            if accuracy_goal < 0:
                raise ValueError
        except ValueError:
            raise ClientErrorException(
                "The accuracy goal value is not valid. "
                "Accuracy goal should be non negative real number.",
            )

        if self.tuning.accuracy_criterion and self.tuning.accuracy_criterion.relative:
            self.tuning.accuracy_criterion.relative = accuracy_goal

    def set_accuracy_metric(self, metric: dict) -> None:
        """Update accuracy metric in config."""
        if (
            self.evaluation
            and self.evaluation.accuracy
            and self.evaluation.accuracy.metric
        ):
            self.evaluation.accuracy.metric.name = metric.get("metric", None)
            self.evaluation.accuracy.metric.param = metric.get("metric_param", None)

    def set_transform(self, transform: List[Dict[str, Any]]) -> None:
        """Set transforms metrics in config."""
        if (
            self.quantization
            and self.quantization.calibration
            and self.quantization.calibration.dataloader
        ):
            self.quantization.calibration.dataloader.transform.clear()
            for single_transform in transform:
                trans_obj = Transform(
                    single_transform["name"],
                    single_transform["params"],
                )
                self.quantization.calibration.dataloader.transform[
                    single_transform["name"]
                ] = deepcopy(trans_obj)

        if (
            self.evaluation
            and self.evaluation.accuracy
            and self.evaluation.accuracy.dataloader
        ):
            self.evaluation.accuracy.dataloader.transform.clear()
            for single_transform in transform:
                trans_obj = Transform(
                    single_transform["name"],
                    single_transform["params"],
                )
                self.evaluation.accuracy.dataloader.transform[
                    single_transform["name"]
                ] = deepcopy(trans_obj)

        if (
            self.evaluation
            and self.evaluation.performance
            and self.evaluation.performance.dataloader
        ):
            self.evaluation.performance.dataloader.transform.clear()
            for single_transform in transform:
                trans_obj = Transform(
                    single_transform["name"],
                    single_transform["params"],
                )
                self.evaluation.performance.dataloader.transform[
                    single_transform["name"]
                ] = deepcopy(trans_obj)

    def set_quantization_approach(self, approach: str) -> None:
        """Update quantization approach in config."""
        if self.quantization:
            self.quantization.approach = str(approach)

    def set_model_path(self, path: str) -> None:
        """Update model_path in config."""
        self.model_path = str(path)

    def set_inputs(self, inputs: List[str]) -> None:
        """Update inputs in config."""
        self.model.inputs = inputs

    def set_outputs(self, outputs: List[str]) -> None:
        """Update outputs in config."""
        self.model.outputs = outputs

    def set_quantization_sampling_size(self, sampling_size: str) -> None:
        """Update quantization sampling size in config."""
        if self.quantization and self.quantization.calibration:
            self.quantization.calibration.sampling_size = str(sampling_size)

    def set_performance_warmup(self, warmup: int) -> None:
        """Update performance evaluation warmup iteration number."""
        try:
            warmup = int(warmup)
            if warmup < 0:
                raise ValueError
        except ValueError:
            raise ClientErrorException(
                "The warmup iterations number is not valid. "
                "Warmup iterations number should be non negative integer.",
            )
        if self.evaluation and self.evaluation.performance:
            self.evaluation.performance.warmup = warmup

    def set_performance_iterations(self, iterations: int) -> None:
        """Update performance evaluation iteration number."""
        try:
            iterations = int(iterations)
            if iterations < -1:
                raise ValueError
        except ValueError:
            raise ClientErrorException(
                "The number of iterations is not valid. "
                "Number of iterations should be non negative integer.",
            )
        if self.evaluation and self.evaluation.performance:
            self.evaluation.performance.iteration = iterations

    def load(self, path: str) -> None:
        """Load configuration from file."""
        log.debug(f"Loading predefined config from {path}")
        with open(path) as yaml_config:
            config = yaml.round_trip_load(yaml_config, preserve_quotes=True)
        self.initialize(config)

    def dump(self, yaml_path: str) -> None:
        """Dump configuration to file."""
        yaml_content = yaml.round_trip_dump(
            data=self.serialize(),
            indent=4,
            default_flow_style=False,
        )

        with open(yaml_path, "w") as yaml_config:
            yaml_config.write(yaml_content)