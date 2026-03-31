"""
firebase_config.py
Firebase Admin SDK 초기화 및 클라이언트 제공
- Streamlit Cloud: st.secrets에서 인증 정보 로드
- 로컬: firebase_credentials.json 파일 사용
"""

import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage


@st.cache_resource
def _initialize_firebase():
    """Firebase 앱 초기화 (앱 수명 동안 1회만 실행)"""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # 1) Streamlit Cloud: st.secrets 사용
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        # private_key의 \\n을 실제 줄바꿈으로 변환
        if "private_key" in firebase_secrets:
            firebase_secrets["private_key"] = firebase_secrets["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(firebase_secrets)
        bucket_name = st.secrets.get("STORAGE_BUCKET", "")
        app = firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        return app
    except (KeyError, FileNotFoundError):
        pass

    # 2) 로컬: firebase_credentials.json 파일 사용
    import os
    cred_path = os.path.join(os.path.dirname(__file__), "firebase_credentials.json")
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        # credentials.json에서 project_id 추출하여 bucket 이름 생성
        with open(cred_path, "r") as f:
            cred_data = json.load(f)
        project_id = cred_data.get("project_id", "")
        bucket_name = os.environ.get("STORAGE_BUCKET", f"{project_id}.firebasestorage.app")
        app = firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        return app

    raise RuntimeError(
        "Firebase 인증 정보를 찾을 수 없습니다.\n"
        "- Streamlit Cloud: st.secrets에 [firebase] 섹션을 추가하세요.\n"
        "- 로컬: firebase_credentials.json 파일을 프로젝트 루트에 배치하세요."
    )


def get_firestore_client():
    """Firestore 클라이언트 반환"""
    _initialize_firebase()
    return firestore.client()


def get_storage_bucket():
    """Firebase Storage 버킷 반환"""
    _initialize_firebase()
    return storage.bucket()
