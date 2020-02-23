from torch.utils.data import Dataset
import scipy.io as scio


class MatLabDataset(Dataset):
    def __init__(self, data_mat_file, label_mat_file):
        super().__init__()
        self.data = scio.loadmat(data_mat_file)["Ds"]
        self.labels = scio.loadmat(label_mat_file)["Ls"]
        if len(self.data) != len(self.labels):
            raise RuntimeError("unmatched mat files")

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]
