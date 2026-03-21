# -*- coding: utf-8 -*-
"""
云存储抽象：支持 S3/R2/OSS 等，生图后上传到云端，返回公网 URL。
阿里云 OSS 使用官方 oss2 库（boto3 与 OSS 存在兼容性问题）。
未配置时 is_cloud_enabled() 返回 False，调用方回退到本地 image_cache。
"""
import re
from pathlib import Path
from typing import Optional, Union

# 延迟导入，避免未安装时影响启动
_oss_bucket = None
_boto3_client = None


def _is_aliyun_oss(cfg) -> bool:
    """是否阿里云 OSS（用 oss2 而非 boto3）。"""
    endpoint = (cfg.get("endpoint") or "").strip()
    return bool(endpoint and "aliyuncs.com" in endpoint)


def _get_oss_bucket():
    """懒加载阿里云 OSS Bucket（oss2）。"""
    global _oss_bucket
    if _oss_bucket is not None:
        return _oss_bucket
    cfg = _get_config()
    if not cfg or not _is_aliyun_oss(cfg):
        return None
    try:
        import oss2

        endpoint = (cfg.get("endpoint") or "").strip()
        endpoint_host = re.sub(r"^https?://", "", endpoint).rstrip("/")
        access_key = (cfg.get("access_key") or "").strip()
        secret_key = (cfg.get("secret_key") or "").strip()
        bucket_name = (cfg.get("bucket") or "").strip()
        if not all([endpoint_host, access_key, secret_key, bucket_name]):
            return None

        auth = oss2.Auth(access_key, secret_key)
        _oss_bucket = oss2.Bucket(auth, endpoint_host, bucket_name)
        return _oss_bucket
    except ImportError:
        print("⚠️ [cloud_storage] 阿里云 OSS 需安装 oss2：pip install oss2")
        return None
    except Exception as e:
        print(f"⚠️ [cloud_storage] 初始化 OSS 失败：{e}")
        return None


def _get_boto3_client():
    """懒加载 S3 客户端（R2 / AWS S3）。"""
    global _boto3_client
    if _boto3_client is not None:
        return _boto3_client
    cfg = _get_config()
    if not cfg or _is_aliyun_oss(cfg):
        return None
    try:
        import boto3
        from botocore.config import Config

        endpoint = (cfg.get("endpoint") or "").strip()
        region = (cfg.get("region") or "auto").strip()
        access_key = (cfg.get("access_key") or "").strip()
        secret_key = (cfg.get("secret_key") or "").strip()
        if not access_key or not secret_key:
            return None

        config = Config(signature_version="s3v4")
        if endpoint:
            _boto3_client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=config,
            )
        else:
            _boto3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region or "us-east-1",
                config=config,
            )
        return _boto3_client
    except ImportError:
        print("⚠️ [cloud_storage] 未安装 boto3，云存储不可用。pip install boto3")
        return None
    except Exception as e:
        print(f"⚠️ [cloud_storage] 初始化 S3 客户端失败：{e}")
        return None


def _get_config():
    """从 config 模块读取云存储配置。"""
    try:
        from src.config import CLOUD_STORAGE_CONFIG
        return CLOUD_STORAGE_CONFIG if isinstance(CLOUD_STORAGE_CONFIG, dict) else None
    except ImportError:
        return None


def is_cloud_enabled() -> bool:
    """是否配置了云存储。"""
    cfg = _get_config()
    if not cfg:
        return False
    provider = (cfg.get("provider") or "").strip().lower()
    bucket = (cfg.get("bucket") or "").strip()
    access_key = (cfg.get("access_key") or "").strip()
    secret_key = (cfg.get("secret_key") or "").strip()
    return bool(provider in ("s3", "r2", "oss") and bucket and access_key and secret_key)


def upload_image(
    data: bytes,
    key: str,
    content_type: str = "image/png",
) -> Optional[str]:
    """
    上传图片到云存储，返回公网 URL。
    :param data: 图片二进制
    :param key: 对象键（如 image_cache/xxx.png）
    :param content_type: MIME 类型
    :return: 公网 URL，失败返回 None
    """
    if not is_cloud_enabled():
        return None
    cfg = _get_config()
    if not cfg:
        return None

    bucket_name = (cfg.get("bucket") or "").strip()
    prefix = (cfg.get("prefix") or "").strip()
    cdn_url = (cfg.get("cdn_url") or "").strip().rstrip("/")
    endpoint = (cfg.get("endpoint") or "").strip()

    object_key = f"{prefix}{key}" if prefix else key

    try:
        if _is_aliyun_oss(cfg):
            # 阿里云 OSS：使用 oss2 库（boto3 与 OSS 存在兼容性问题）
            oss_bucket = _get_oss_bucket()
            if not oss_bucket:
                return None
            oss_bucket.put_object(object_key, data, headers={"Content-Type": content_type})
            if cdn_url:
                return f"{cdn_url}/{object_key}"
            endpoint_host = re.sub(r"^https?://", "", endpoint).rstrip("/")
            return f"https://{bucket_name}.{endpoint_host}/{object_key}"
        else:
            # R2 / AWS S3：使用 boto3
            client = _get_boto3_client()
            if not client:
                return None
            client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )
            if cdn_url:
                return f"{cdn_url}/{object_key}"
            if endpoint and ("r2.cloudflarestorage.com" in endpoint or "r2.dev" in endpoint):
                print("⚠️ [cloud_storage] R2 需配置 CLOUD_STORAGE_CDN_URL 才能返回公网 URL，已回退到本地")
                return None
            if endpoint:
                base = endpoint.rstrip("/")
                return f"{base}/{bucket_name}/{object_key}"
            region = (cfg.get("region") or "us-east-1").strip()
            if region == "auto":
                region = "us-east-1"
            return f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_key}"
    except Exception as e:
        print(f"⚠️ [cloud_storage] 上传失败：{e}")
        import traceback
        traceback.print_exc()
        return None


def download_oss_to_file(url: str, out_path: Union[str, Path]) -> bool:
    """
    从 OSS URL 下载到本地文件。当桶未开放公共读时，用 oss2 带凭证下载。
    :return: 成功返回 True
    """
    if not url or not str(url).strip().startswith(("http://", "https://")):
        return False
    url = str(url).strip()
    cfg = _get_config()
    if not cfg or not _is_aliyun_oss(cfg):
        return False
    bucket_name = (cfg.get("bucket") or "").strip()
    endpoint_host = (cfg.get("endpoint") or "").strip()
    endpoint_host = re.sub(r"^https?://", "", endpoint_host).rstrip("/")
    cdn_url = (cfg.get("cdn_url") or "").strip().rstrip("/")
    # 检查 URL 是否属于当前配置的 OSS
    is_our_oss = (bucket_name and bucket_name in url) or (endpoint_host and endpoint_host in url) or (cdn_url and url.startswith(cdn_url))
    if not is_our_oss:
        return False
    # 从 URL 提取 object key：https://bucket.endpoint/key 或 https://cdn/key
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
        if not path:
            return False
        object_key = path
        oss_bucket = _get_oss_bucket()
        if not oss_bucket:
            return False
        result = oss_bucket.get_object(object_key)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(result.read())
        return out_path.exists()
    except Exception as e:
        print(f"⚠️ [cloud_storage] OSS 下载失败：{e}")
        return False
