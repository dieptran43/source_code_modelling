import torch
import torch.nn
from labml import experiment, logger
from labml.helpers.pytorch.module import Module
from labml.logger import Text, Style
from labml.utils.pytorch import get_modules

from train import Configs, TextDataset


class Predictor:
    """
    Predicts the next few characters
    """

    def __init__(self, model: Module, dataset: TextDataset):
        self.dataset = dataset
        self.model = model

        # Initial state
        self._h0 = None
        self._c0 = None
        self._last_char = None

        # For timing
        self.time_add = 0
        self.time_predict = 0
        self.time_check = 0

    def get_predictions(self, char: str) -> torch.Tensor:
        data = torch.tensor([[self.dataset.stoi[char]]],
                            dtype=torch.long,
                            device=self.model.device)
        # Get predictions
        prediction, (h0, c0) = self.model(data, self._h0, self._c0)

        self._h0 = h0
        self._c0 = c0

        # Final prediction
        prediction = prediction[-1, :, :]

        return prediction.detach().cpu().numpy()

    def get_suggestion(self, char: str) -> str:
        prediction = self.get_predictions(char)
        best = prediction.argmax(-1).squeeze().item()
        return self.dataset.itos[best]


class Evaluator:
    def __init__(self, model: Module, dataset: TextDataset, text: str):
        self.text = text
        self.predictor = Predictor(model, dataset)

    def eval(self):
        line_no = 1
        logs = [(f"{line_no: 4d}: ", Text.meta), (self.text[0], Text.subtle)]

        correct = 0

        for i in range(len(self.text) - 1):
            next_char = self.predictor.get_suggestion(self.text[i])
            if next_char == self.text[i + 1]:
                correct += 1
            if self.text[i + 1] == '\n':
                logger.log(logs)
                line_no += 1
                logs = [(f"{line_no: 4d}: ", Text.meta)]
            elif self.text[i + 1] == '\r':
                continue
            else:
                if next_char == self.text[i + 1]:
                    logs.append((self.text[i + 1], Style.underline))
                else:
                    logs.append((self.text[i + 1], Text.subtle))

            # Log the line
        logger.log(logs)

        # Log time taken for the file
        logger.log("Accuracy: ", (f"{correct / (len(self.text) - 1) :.2f}", Text.value))


def main():
    conf = Configs()
    experiment.create(name="source_code",
                      comment='lstm model')

    # Replace this with your training experiment UUID
    conf_dict = experiment.load_configs('9c8c24fae75c11ea8e22551c650c3796')
    experiment.configs(conf, conf_dict, 'run')
    experiment.add_pytorch_models(get_modules(conf))
    experiment.load('9c8c24fae75c11ea8e22551c650c3796')

    evaluator = Evaluator(conf.model, conf.text, conf.text.valid)
    evaluator.eval()


if __name__ == '__main__':
    main()
