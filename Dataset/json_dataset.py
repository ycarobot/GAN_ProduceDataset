from torch.utils.data import Dataset
import torch
import scipy.io as scio
import json


class JSONDataset(Dataset):
    def __init__(self, data_file, label_file):
        super().__init__()
        self.data = json.load(open(data_file, "r"))["Ds"]
        self.labels = json.load(open(label_file, "r"))["Ls"]
        if len(self.data) != len(self.labels):
            raise RuntimeError("unmatched mat files")

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return torch.Tensor(self.data[idx]), torch.Tensor(self.labels[idx])
