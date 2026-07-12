from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from artist_portrait_editor.constants import SCHEMA_VERSION

class BgmMatchCandidate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    music_candidate_id:str; input_mode:str; mixed_audio:bool
    mood_fit:Literal["unknown","poor","partial","good"]="unknown"
    rhythm_fit:Literal["unknown","poor","partial","good"]="unknown"
    mood_confidence:float=Field(ge=0,le=1); rhythm_confidence:float=Field(ge=0,le=1)
    bpm:float|None=None; beat_status:str
    ducking_pressure:Literal["low","medium","high"]
    text_timing_pressure:Literal["low","medium","high"]
    transition_pressure:Literal["low","medium","high"]
    source_risks:list[str]=Field(default_factory=list); compatible_option_ids:list[str]=Field(default_factory=list)

class BgmMatchReport(BaseModel):
    model_config=ConfigDict(extra="forbid")
    schema_version:str=SCHEMA_VERSION; bgm_match_id:str; project_id:str
    structure_ref:str; structure_fingerprint:str=Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_state:Literal["direct_audio","video_audio_extract","source_embedded_audio","multiple_candidates","no_file_yet"]
    candidate_count:int=Field(ge=0); candidates:list[BgmMatchCandidate]=Field(default_factory=list)
    status:Literal["ready","degraded","planning_only"]; summary:str; warnings:list[str]=Field(default_factory=list)
    automatic_music_selection:bool=False; selected_candidate_id:str|None=None
    fabricated_mood:bool=False; fabricated_bpm_or_beats:bool=False; timeline_mutated:bool=False; media_rendered:bool=False; model_call_performed_by_cli:bool=False; network_performed:bool=False
