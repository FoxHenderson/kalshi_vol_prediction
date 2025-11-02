# predict_from_file.py
import json
import pickle
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

def load_model():
    """Load the trained model and artifacts"""
    with open('volume_prediction_model.pkl', 'rb') as f:
        pipe = pickle.load(f)
    
    with open('model_artifacts.pkl', 'rb') as f:
        artifacts = pickle.load(f)
    
    return pipe, artifacts

def preprocess_new_data(data_json, artifacts):
    # convert to df
    if isinstance(data_json, dict):
        df = pd.DataFrame([data_json])
    else:
        df = pd.DataFrame(data_json)
    
    df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
    df["can_close_early"] = df["can_close_early"].astype(int)
    
    titles = df['title'].tolist()
    sentence_model = SentenceTransformer(artifacts['sentence_model_name'])  # FIXED
    title_embeddings = sentence_model.encode(titles)
    
    pca = artifacts['pca']
    title_emb_reduced = pca.transform(title_embeddings)
    
    # create embedding df
    title_emb_cols = artifacts['title_emb_cols']
    title_emb_df = pd.DataFrame(title_emb_reduced, columns=title_emb_cols)
    df = pd.concat([df.reset_index(drop=True), title_emb_df.reset_index(drop=True)], axis=1)
    
    df['is_major_event'] = df['title'].str.contains(
        'championship|final|cup|election|champion', 
        case=False, regex=True
    ).astype(int)
    
    df['is_major_sport'] = df['title'].str.contains(
        'NFL|NBA|MLB|Premier League', 
        case=False, regex=True
    ).astype(int)
    
    feature_cols = artifacts['feature_cols']
    X = df[feature_cols]
    
    return X, df


def predict_volume(data_json):
    pipe, artifacts = load_model()

    X, df_full = preprocess_new_data(data_json, artifacts)

    y_pred_log = pipe.predict(X)
    y_pred = np.expm1(y_pred_log)
    
    return y_pred, df_full


def predict_from_json_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    predictions, df = predict_volume(data)
    
    results = []
    for idx, pred in enumerate(predictions):
        results.append({
            'title': df['title'].iloc[idx],
            'category': df['category'].iloc[idx],
            'predicted_volume': int(pred),
            'duration': df['duration'].iloc[idx]
        })
    
    return results

if __name__ == "__main__":
    results = predict_from_json_file('test.json')
    
    for r in results:
        print(f"\n{r['title']}")
        print(f"  Category: {r['category']}")
        print(f"  Predicted Volume: {r['predicted_volume']:,}")
