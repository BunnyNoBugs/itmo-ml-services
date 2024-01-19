from fastapi import FastAPI, File, UploadFile
from io import StringIO
import pandas as pd

from ml.model import load_model

app = FastAPI()


# create a route
@app.get("/")
def index():
    return {"text": "Sentiment Analysis"}


@app.on_event("startup")
def startup_event():
    global model
    model = load_model()


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    input_df = pd.read_csv(StringIO(contents.decode()))
    pred = model.predict(input_df)
    print(pred)
    return None
