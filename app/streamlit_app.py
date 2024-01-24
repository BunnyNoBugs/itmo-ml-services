import streamlit as st
import requests

st.title('Software classification')

st.subheader('Authorization')

if 'access_token' not in st.session_state:
    st.session_state.access_token = None

col1, col2 = st.columns([1, 1])

with col1:
    st.write('Please login to use the service:')
    with st.form('login_form'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        login_button = st.form_submit_button('Login')

        if login_button:
            login_data = {
                "username": username,
                "password": password
            }
            login_response = requests.post(url="http://127.0.0.1:8000/token", data=login_data)
            if login_response.status_code == 200:
                st.session_state.access_token = login_response.json().get('access_token')
                st.write('Login successful!')
            else:
                st.error('Username/password is incorrect')
with col2:
    st.write('Need to create a new user?')
    with st.form('user_create_form'):
        username = st.text_input('Username')
        email = st.text_input('Email')
        password = st.text_input('Password', type='password')
        user_create_button = st.form_submit_button('Create user')

    if user_create_button:
        user_create_data = {
            'username': username,
            'email': email,
            'password': password
        }
        user_create_response = requests.post(url="http://127.0.0.1:8000/users/", json=user_create_data)
        if user_create_response.status_code == 200:
            st.write('User created!')
        else:
            st.error('Email already registered')

st.subheader('Making predictions')

model_type_name = st.radio('Choose classification model type:',
                           ['Logistic regression', 'Random forest', 'Gradient boosting'],
                           captions=['5 credits', '5 credits', '10 credits'],
                           horizontal=True)
model_type_names = {
    'Logistic regression': 'lr',
    'Random forest': 'rf',
    'Gradient boosting': 'gb'
}
model_type = model_type_names[model_type_name]

input_csv_file = st.file_uploader('Choose a CSV file with input features:')
if input_csv_file is not None:
    bytes_data = input_csv_file.getvalue()

    predict_button = st.button('Predict', type='primary')
    if predict_button:
        files = {
            'file': bytes_data
        }
        params = {
            'requested_model_type': model_type
        }
        headers = {
            'Authorization': f'Bearer {st.session_state.access_token}'

        }
        predict_response = requests.post(url="http://127.0.0.1:8000/predict", files=files, params=params,
                                         headers=headers)
        if predict_response.status_code == 200:
            st.write('Prediction made successfully!')
            pred_result = predict_response.json().get('pred_result')
            st.write(
                f'{round(sum(pred_result) / len(pred_result) * 100, 2)}% '
                f'of your dataset have been classified as malware.')
        else:
            st.error(f'{predict_response.json().get("detail")}')
