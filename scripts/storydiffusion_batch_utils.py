from __future__ import annotations

import copy
import os
import random
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Sequence, Tuple

import yaml


@contextmanager
def _pushd(path: Path) -> Iterator[None]:
    old_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def _as_posix(path: Path) -> str:
    return path.as_posix()


def _select_device(requested: str, torch: Any) -> str:
    if requested == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false.")
    return requested


def _select_dtype(dtype_name: str, device: str, torch: Any) -> Any:
    if dtype_name == "auto":
        return torch.float16 if device == "cuda" else torch.float32
    if dtype_name == "float16":
        return torch.float16
    if dtype_name == "bfloat16":
        return torch.bfloat16
    return torch.float32


def _load_models_config(repo_dir: Path) -> Dict[str, Dict[str, Any]]:
    config_path = repo_dir / "config" / "models.yaml"
    with config_path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _character_to_dict(general_prompt: str) -> Tuple[Dict[str, str], List[str]]:
    character_dict: Dict[str, str] = {}
    character_list: List[str] = []
    for line in general_prompt.splitlines():
        start = line.find("[")
        end = line.find("]")
        if start == -1 or end == -1:
            continue
        key = line[start : end + 1]
        value = line[end + 1 :]
        if "#" in value:
            value = value.rpartition("#")[0]
        if key in character_dict:
            raise ValueError(f"duplicate character description: {key}")
        character_dict[key] = value
        character_list.append(key)
    return character_dict, character_list


def _process_original_prompt(
    character_dict: Dict[str, str],
    prompts: Sequence[str],
    id_length: int,
) -> Tuple[Dict[str, List[int]], Dict[int, List[str]], List[str], Dict[str, List[int]], List[int]]:
    replace_prompts: List[str] = []
    character_index_dict: Dict[str, List[int]] = {}
    invert_character_index_dict: Dict[int, List[str]] = {}
    for ind, prompt in enumerate(prompts):
        for key in character_dict.keys():
            if key in prompt:
                character_index_dict.setdefault(key, []).append(ind)
                invert_character_index_dict.setdefault(ind, []).append(key)
        cur_prompt = prompt
        if ind in invert_character_index_dict:
            for key in invert_character_index_dict[ind]:
                cur_prompt = cur_prompt.replace(key, character_dict[key] + " ")
        replace_prompts.append(cur_prompt)

    ref_index_dict: Dict[str, List[int]] = {}
    ref_totals: List[int] = []
    for character_key, index_list_all in character_index_dict.items():
        index_list = [index for index in index_list_all if len(invert_character_index_dict[index]) == 1]
        if len(index_list) < id_length:
            raise ValueError(
                f"{character_key} does not have enough prompt descriptions: "
                f"need at least {id_length}, got {len(index_list)}"
            )
        ref_index_dict[character_key] = index_list[:id_length]
        ref_totals.extend(index_list[:id_length])
    return character_index_dict, invert_character_index_dict, replace_prompts, ref_index_dict, ref_totals


def _get_ref_character(real_prompt: str, character_dict: Dict[str, str]) -> List[str]:
    return [key for key in character_dict.keys() if key in real_prompt]


def _cal_attn_indices_xl(total_length: int, id_length: int, sa32: float, sa64: float, height: int, width: int, device: str, dtype: Any) -> Tuple[List[Any], List[Any]]:
    import torch

    nums_1024 = (height // 32) * (width // 32)
    nums_4096 = (height // 16) * (width // 16)
    bool_matrix1024 = torch.rand((total_length, nums_1024), device=device, dtype=dtype) < sa32
    bool_matrix4096 = torch.rand((total_length, nums_4096), device=device, dtype=dtype) < sa64
    indices1024 = [torch.nonzero(bool_matrix1024[i], as_tuple=True)[0] for i in range(total_length)]
    indices4096 = [torch.nonzero(bool_matrix4096[i], as_tuple=True)[0] for i in range(total_length)]
    return indices1024, indices4096


def _resolve_model_info(repo_dir: Path, model: str, model_path: str | None, single_file: bool) -> Dict[str, Any]:
    models = _load_models_config(repo_dir)
    if model_path:
        path = model_path
        key = model_path
        use_safetensors = path.endswith(".safetensors")
        resolved_single_file = single_file or use_safetensors
    elif model in models:
        info = dict(models[model])
        info["key"] = model
        return info
    else:
        path = model
        key = model
        use_safetensors = path.endswith(".safetensors")
        resolved_single_file = single_file or use_safetensors
    return {
        "key": key,
        "path": path,
        "single_files": resolved_single_file,
        "use_safetensors": use_safetensors,
    }


class StoryDiffusionBatchGenerator:
    def __init__(
        self,
        repo_dir: str | Path,
        model: str,
        model_path: str | None,
        single_file: bool,
        device: str,
        dtype: str,
        attention_slicing: bool,
        cpu_offload: bool,
        vae_slicing: bool,
        freeu: bool,
        local_files_only: bool,
    ) -> None:
        self.repo_dir = Path(repo_dir).resolve()
        if str(self.repo_dir) not in sys.path:
            sys.path.insert(0, str(self.repo_dir))

        import torch
        from diffusers import StableDiffusionXLPipeline
        from diffusers.schedulers.scheduling_ddim import DDIMScheduler

        self.torch = torch
        self.device = _select_device(device, torch)
        self.dtype = _select_dtype(dtype, self.device, torch)
        self.model_info = _resolve_model_info(self.repo_dir, model, model_path, single_file)
        self.model_label = str(self.model_info["path"])

        load_kwargs: Dict[str, Any] = {
            "torch_dtype": self.dtype,
            "local_files_only": local_files_only,
        }
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        if token:
            load_kwargs["token"] = token

        with _pushd(self.repo_dir):
            if self.model_info.get("single_files"):
                self.pipe = StableDiffusionXLPipeline.from_single_file(self.model_info["path"], **load_kwargs)
            else:
                self.pipe = StableDiffusionXLPipeline.from_pretrained(
                    self.model_info["path"],
                    use_safetensors=self.model_info.get("use_safetensors", True),
                    **load_kwargs,
                )

        self.pipe.scheduler = DDIMScheduler.from_config(self.pipe.scheduler.config)
        if freeu and hasattr(self.pipe, "enable_freeu"):
            self.pipe.enable_freeu(s1=0.6, s2=0.4, b1=1.1, b2=1.2)
        if vae_slicing and hasattr(self.pipe, "enable_vae_slicing"):
            self.pipe.enable_vae_slicing()
        if attention_slicing and hasattr(self.pipe, "enable_attention_slicing"):
            self.pipe.enable_attention_slicing()
        if cpu_offload and self.device == "cuda":
            self.pipe.enable_model_cpu_offload()
        else:
            self.pipe = self.pipe.to(self.device)

        self._install_attention_processor(id_length=4)

    def _install_attention_processor(self, id_length: int) -> None:
        from diffusers.models.attention_processor import AttnProcessor2_0

        global total_count, attn_count, cur_step, attn_procs
        total_count = 0
        attn_count = 0
        cur_step = 0
        attn_procs = {}
        unet = self.pipe.unet
        for name in unet.attn_processors.keys():
            cross_attention_dim = None if name.endswith("attn1.processor") else unet.config.cross_attention_dim
            if cross_attention_dim is None and name.startswith("up_blocks"):
                attn_procs[name] = SpatialAttnProcessor2_0(
                    id_length=id_length,
                    device=self.device,
                    dtype=self.dtype,
                )
                total_count += 1
            else:
                attn_procs[name] = AttnProcessor2_0()
        unet.set_attn_processor(copy.deepcopy(attn_procs))

    def _clear_id_bank(self, id_length: int) -> None:
        for attn_processor in self.pipe.unet.attn_processors.values():
            if isinstance(attn_processor, SpatialAttnProcessor2_0):
                attn_processor.id_bank = {}
                attn_processor.id_length = id_length
                attn_processor.total_length = id_length + 1

    def _setup_seed(self, seed: int) -> None:
        import numpy as np

        self.torch.manual_seed(seed)
        if self.device == "cuda":
            self.torch.cuda.manual_seed_all(seed)
        np.random.seed(seed)
        random.seed(seed)
        if hasattr(self.torch.backends, "cudnn"):
            self.torch.backends.cudnn.deterministic = True

    def _generator(self, seed: int) -> Any:
        try:
            return self.torch.Generator(device=self.device).manual_seed(seed)
        except RuntimeError:
            return self.torch.Generator().manual_seed(seed)

    def generate(
        self,
        general_prompt: str,
        prompt_array: Sequence[str],
        visible_indices: Sequence[int],
        seed: int,
        num_inference_steps: int,
        height: int,
        width: int,
        id_length: int,
        sa32: float,
        sa64: float,
        style_name: str,
        negative_prompt: str,
        guidance_scale: float,
    ) -> Tuple[List[Any], Dict[str, Any]]:
        from utils.style_template import styles

        if style_name not in styles:
            raise ValueError(f"Unknown StoryDiffusion style '{style_name}'. Available examples: {list(styles)[:5]}")
        if len(general_prompt.splitlines()) >= 3:
            raise ValueError("The official low-VRAM StoryDiffusion flow supports at most two characters.")

        global character_dict, character_index_dict, invert_character_index_dict, ref_indexs_dict, ref_totals
        global write, cur_step, attn_count, cur_character
        globals()["height"] = height
        globals()["width"] = width
        globals()["sa32"] = sa32
        globals()["sa64"] = sa64

        self._install_attention_processor(id_length=id_length)
        self._clear_id_bank(id_length=id_length)

        prompts = list(prompt_array)
        character_dict, _character_list = _character_to_dict(general_prompt)
        (
            character_index_dict,
            invert_character_index_dict,
            replace_prompts,
            ref_indexs_dict,
            ref_totals,
        ) = _process_original_prompt(character_dict, prompts.copy(), id_length)

        def apply_style_positive(positive: str) -> str:
            return styles[style_name][0].replace("{prompt}", positive)

        def apply_style(positives: Sequence[str], negative: str) -> Tuple[List[str], str]:
            styled = [apply_style_positive(positive) for positive in positives]
            styled_negative = styles[style_name][1] + negative
            return styled, styled_negative

        results_dict: Dict[int, Any] = {}
        write = True
        for character_key in character_dict.keys():
            cur_character = [character_key]
            current_prompts = [replace_prompts[ref_ind] for ref_ind in ref_indexs_dict[character_key]]
            self._setup_seed(seed)
            cur_step = 0
            attn_count = 0
            positive_prompts, styled_negative = apply_style(current_prompts, negative_prompt)
            id_images = self.pipe(
                positive_prompts,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                height=height,
                width=width,
                negative_prompt=styled_negative,
                generator=self._generator(seed),
            ).images
            for ind, image in enumerate(id_images):
                results_dict[ref_indexs_dict[character_key][ind]] = image

        write = False
        real_prompt_indices = [ind for ind in range(len(prompts)) if ind not in ref_totals]
        for real_prompt_index in real_prompt_indices:
            real_prompt = replace_prompts[real_prompt_index]
            cur_character = _get_ref_character(prompts[real_prompt_index], character_dict)
            self._setup_seed(seed)
            cur_step = 0
            attn_count = 0
            results_dict[real_prompt_index] = self.pipe(
                apply_style_positive(real_prompt),
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                height=height,
                width=width,
                negative_prompt=negative_prompt,
                generator=self._generator(seed),
            ).images[0]

        selected_indices = list(visible_indices) or sorted(results_dict)
        missing = [ind for ind in selected_indices if ind not in results_dict]
        if missing:
            raise RuntimeError(f"StoryDiffusion did not return images for prompt indices: {missing}")
        images = [results_dict[ind] for ind in selected_indices]
        metadata = {
            "device": self.device,
            "dtype": str(self.dtype).replace("torch.", ""),
            "num_inference_steps": num_inference_steps,
            "height": height,
            "width": width,
            "guidance_scale": guidance_scale,
            "style": style_name,
            "id_length": id_length,
            "sa32": sa32,
            "sa64": sa64,
        }
        if self.device == "cuda":
            props = self.torch.cuda.get_device_properties(0)
            metadata["gpu"] = props.name
            metadata["gpu_total_memory_gb"] = round(props.total_memory / (1024**3), 2)
        return images, metadata


class SpatialAttnProcessor2_0(__import__("torch").nn.Module):
    def __init__(self, hidden_size: int | None = None, cross_attention_dim: int | None = None, id_length: int = 4, device: str = "cuda", dtype: Any = None):
        import torch
        import torch.nn.functional as F

        super().__init__()
        if not hasattr(F, "scaled_dot_product_attention"):
            raise ImportError("AttnProcessor2_0 requires PyTorch 2.0 or newer.")
        self.device = device
        self.dtype = dtype or torch.float16
        self.hidden_size = hidden_size
        self.cross_attention_dim = cross_attention_dim
        self.total_length = id_length + 1
        self.id_length = id_length
        self.id_bank: Dict[str, Dict[int, List[Any]]] = {}

    def __call__(self, attn: Any, hidden_states: Any, encoder_hidden_states: Any = None, attention_mask: Any = None, temb: Any = None) -> Any:
        global total_count, attn_count, cur_step, indices1024, indices4096
        global sa32, sa64, write, height, width, cur_character
        if attn_count == 0 and cur_step == 0:
            indices1024, indices4096 = _cal_attn_indices_xl(
                self.total_length,
                self.id_length,
                sa32,
                sa64,
                height,
                width,
                device=self.device,
                dtype=self.dtype,
            )
        if write:
            if len(cur_character) != 1:
                raise RuntimeError("Reference-bank writing expects exactly one current character.")
            indices = indices1024 if hidden_states.shape[1] == (height // 32) * (width // 32) else indices4096
            total_batch_size, nums_token, channel = hidden_states.shape
            img_nums = total_batch_size // 2
            bank_states = hidden_states.reshape(-1, img_nums, nums_token, channel)
            self.id_bank.setdefault(cur_character[0], {})
            self.id_bank[cur_character[0]][cur_step] = [
                bank_states[:, img_ind, indices[img_ind], :].reshape(2, -1, channel).clone()
                for img_ind in range(img_nums)
            ]
            hidden_states = bank_states.reshape(-1, nums_token, channel)
        else:
            encoder_arr = []
            for character in cur_character:
                if character in self.id_bank and cur_step in self.id_bank[character]:
                    encoder_arr.extend(tensor.to(self.device) for tensor in self.id_bank[character][cur_step])

        if cur_step < 1:
            hidden_states = self._standard_attention(attn, hidden_states, None, attention_mask, temb)
        else:
            random_number = random.random()
            rand_num = 0.3 if cur_step < 20 else 0.1
            if random_number > rand_num:
                indices = indices1024 if hidden_states.shape[1] == (height // 32) * (width // 32) else indices4096
                if write:
                    total_batch_size, nums_token, channel = hidden_states.shape
                    img_nums = total_batch_size // 2
                    hidden_states = hidden_states.reshape(-1, img_nums, nums_token, channel)
                    encoder_arr = [
                        hidden_states[:, img_ind, indices[img_ind], :].reshape(2, -1, channel)
                        for img_ind in range(img_nums)
                    ]
                    for img_ind in range(img_nums):
                        other_indices = [i for i in range(img_nums) if i != img_ind]
                        encoder_hidden_states_tmp = torch_cat(
                            [encoder_arr[i] for i in other_indices] + [hidden_states[:, img_ind, :, :]],
                            dim=1,
                        )
                        hidden_states[:, img_ind, :, :] = self._standard_attention(
                            attn,
                            hidden_states[:, img_ind, :, :],
                            encoder_hidden_states_tmp,
                            None,
                            temb,
                        )
                else:
                    _, nums_token, channel = hidden_states.shape
                    hidden_states = hidden_states.reshape(2, -1, nums_token, channel)
                    encoder_hidden_states_tmp = torch_cat(encoder_arr + [hidden_states[:, 0, :, :]], dim=1)
                    hidden_states[:, 0, :, :] = self._standard_attention(
                        attn,
                        hidden_states[:, 0, :, :],
                        encoder_hidden_states_tmp,
                        None,
                        temb,
                    )
                hidden_states = hidden_states.reshape(-1, nums_token, channel)
            else:
                hidden_states = self._standard_attention(attn, hidden_states, None, attention_mask, temb)

        attn_count += 1
        if attn_count == total_count:
            attn_count = 0
            cur_step += 1
            indices1024, indices4096 = _cal_attn_indices_xl(
                self.total_length,
                self.id_length,
                sa32,
                sa64,
                height,
                width,
                device=self.device,
                dtype=self.dtype,
            )
        return hidden_states

    def _standard_attention(self, attn: Any, hidden_states: Any, encoder_hidden_states: Any = None, attention_mask: Any = None, temb: Any = None) -> Any:
        import torch.nn.functional as F

        residual = hidden_states
        if attn.spatial_norm is not None:
            hidden_states = attn.spatial_norm(hidden_states, temb)
        input_ndim = hidden_states.ndim
        if input_ndim == 4:
            batch_size, channel, local_height, local_width = hidden_states.shape
            hidden_states = hidden_states.view(batch_size, channel, local_height * local_width).transpose(1, 2)

        batch_size, sequence_length, channel = hidden_states.shape
        if attention_mask is not None:
            attention_mask = attn.prepare_attention_mask(attention_mask, sequence_length, batch_size)
            attention_mask = attention_mask.view(batch_size, attn.heads, -1, attention_mask.shape[-1])
        if attn.group_norm is not None:
            hidden_states = attn.group_norm(hidden_states.transpose(1, 2)).transpose(1, 2)

        query = attn.to_q(hidden_states)
        if encoder_hidden_states is None:
            encoder_hidden_states = hidden_states
        key = attn.to_k(encoder_hidden_states)
        value = attn.to_v(encoder_hidden_states)
        inner_dim = key.shape[-1]
        head_dim = inner_dim // attn.heads
        query = query.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        key = key.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        value = value.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        hidden_states = F.scaled_dot_product_attention(query, key, value, attn_mask=attention_mask, dropout_p=0.0, is_causal=False)
        hidden_states = hidden_states.transpose(1, 2).reshape(batch_size, -1, attn.heads * head_dim)
        hidden_states = hidden_states.to(query.dtype)
        hidden_states = attn.to_out[0](hidden_states)
        hidden_states = attn.to_out[1](hidden_states)

        if input_ndim == 4:
            hidden_states = hidden_states.transpose(-1, -2).reshape(batch_size, channel, local_height, local_width)
        if attn.residual_connection:
            hidden_states = hidden_states + residual
        return hidden_states / attn.rescale_output_factor


def torch_cat(tensors: Sequence[Any], dim: int) -> Any:
    import torch

    return torch.cat(list(tensors), dim=dim)


def save_storydiffusion_outputs(
    repo_dir: str | Path,
    output_dir: str | Path,
    sample_id: str,
    images: Sequence[Any],
    prompt_array: Sequence[str],
    comic_type: str,
    font_name: str,
) -> Dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    frame_paths: List[str] = []
    for index, image in enumerate(images, start=1):
        frame_path = output_path / f"{sample_id}_frame_{index:03d}.png"
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(frame_path)
        frame_paths.append(_as_posix(frame_path))

    primary = frame_paths[0]
    all_paths = list(frame_paths)
    if comic_type != "No typesetting (default)":
        font_path = Path(repo_dir) / "fonts" / font_name
        font = ImageFont.truetype(str(font_path), 18) if font_path.exists() else ImageFont.load_default()
        frame_width, frame_height = images[0].size
        caption_height = 96
        cell_width = frame_width
        cell_height = frame_height + caption_height
        cols = 2 if comic_type == "Four Pannel" else min(3, max(1, len(images)))
        rows = (len(images) + cols - 1) // cols
        comic = Image.new("RGB", (cols * cell_width, rows * cell_height), "white")
        draw = ImageDraw.Draw(comic)
        for index, image in enumerate(images):
            row = index // cols
            col = index % cols
            x = col * cell_width
            y = row * cell_height
            comic.paste(image.convert("RGB"), (x, y))
            caption = prompt_array[index] if index < len(prompt_array) else ""
            caption = caption.replace("[NC]", "").replace("\n", " ")
            wrapped_caption = "\n".join(textwrap.wrap(caption[:180], width=72)[:3])
            draw.multiline_text((x + 12, y + frame_height + 10), wrapped_caption, fill="black", font=font, spacing=4)
            draw.rectangle((x, y, x + cell_width - 1, y + cell_height - 1), outline="black", width=3)
        comic_path = output_path / f"{sample_id}.png"
        comic_path.parent.mkdir(parents=True, exist_ok=True)
        comic.save(comic_path)
        primary = _as_posix(comic_path)
        all_paths.insert(0, primary)

    return {"primary": primary, "frames": frame_paths, "all": all_paths}
