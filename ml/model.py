from dataclasses import dataclass
import pickle
import pandas as pd


def load_model(model_type: str = 'lr'):
    with open(f'models/{model_type}_model.pickle', 'rb') as f:
        model_instance = pickle.load(f)

    return model_instance
