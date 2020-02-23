import scipy.io as scio
import json


def to_json(mat_file):
    data = scio.loadmat(mat_file)
    new_data = {}
    for key in data.keys():
        if key == "Ds" or key == "Ls":
            new_data[key] = data[key].tolist()
    open(mat_file + ".json", "w").write(json.dumps(new_data))


to_json("OfficeCaltech_1_SourceData.mat")
to_json("OfficeCaltech_1_SourceLabel.mat")
to_json("OfficeCaltech_1_TargetData.mat")
to_json("OfficeCaltech_1_TargetLabel.mat")
