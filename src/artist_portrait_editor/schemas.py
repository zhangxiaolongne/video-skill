from __future__ import annotations

import json
from pathlib import Path

from artist_portrait_editor.models.acceptance import ProjectAcceptanceReport
from artist_portrait_editor.models.aesthetic_baseline import AestheticBaseline
from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.bgm import (
    BgmAnalysisReport,
    BgmBeatGrid,
    BgmCandidateLedger,
    BgmFitPlan,
    BgmRhythmIntelligenceReport,
)
from artist_portrait_editor.models.bgm_recommendation import (
    BgmRecommendationContext,
    BgmRecommendationFitReview,
    BgmRecommendationSelection,
    BgmRecommendationSet,
    BgmRecommendationValidationReport,
)
from artist_portrait_editor.models.bgm_match import BgmMatchReport
from artist_portrait_editor.models.benchmark_pack import RealVideoBenchmarkPack
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.clip_score import ClipScoreRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.composition import CompositionReview
from artist_portrait_editor.models.creative_strategy import CreativeStrategyPackage
from artist_portrait_editor.models.reframe import ReframeApplication, ReframeSelection
from artist_portrait_editor.models.cut_review import CutReviewReport
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.evidence_map import EvidenceMap
from artist_portrait_editor.models.editor_package import EditorPackage
from artist_portrait_editor.models.editorial_score import EditorialScoreSet
from artist_portrait_editor.models.fcpxml import (
    FcpxmlDraft,
    FcpxmlImportReview,
    FcpxmlImportReviewCandidate,
    FcpxmlRepairPlan,
    FcpxmlValidationReport,
)
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.final_export import (
    FinalExportManifest,
    FinalExportValidationReport,
)
from artist_portrait_editor.models.nle_interchange import NleInterchangePlan
from artist_portrait_editor.models.operator import OperatorRunbook
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.models.preview import PreviewRenderManifest, PreviewValidationReport
from artist_portrait_editor.models.release import ReleaseHardeningReport
from artist_portrait_editor.models.revision import RevisionPlan
from artist_portrait_editor.models.revision_application import RevisionApplication
from artist_portrait_editor.models.revision_promotion import RevisionPromotion
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.sound import SoundDecision
from artist_portrait_editor.models.style_template import StyleTemplatePackage
from artist_portrait_editor.models.structure_recommendation import StructureRecommendation
from artist_portrait_editor.models.second_cut import SecondCutCandidate
from artist_portrait_editor.models.rhythm import (
    EditGuidanceReport,
    RhythmAgentCandidate,
    RhythmIntent,
    RhythmMediaQcReport,
    RhythmPlan,
    RhythmRepairPlan,
)
from artist_portrait_editor.models.transcript import TranscriptRecord
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport
from artist_portrait_editor.models.text_plan import TextTimingPlan
from artist_portrait_editor.models.first_cut_review import FirstCutSelfReview
from artist_portrait_editor.models.second_cut_render import SecondCutRender
from artist_portrait_editor.models.workflow import (
    WorkflowExecutionRecord,
    WorkflowExecutionReview,
    WorkflowPlan,
)


def write_schema_files(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    schemas = {
        "analysis_record.schema.json": AnalysisRecord.model_json_schema(),
        "aesthetic_baseline.schema.json": AestheticBaseline.model_json_schema(),
        "project_acceptance_report.schema.json": ProjectAcceptanceReport.model_json_schema(),
        "bgm_analysis_report.schema.json": BgmAnalysisReport.model_json_schema(),
        "bgm_match_report.schema.json": BgmMatchReport.model_json_schema(),
        "real_video_benchmark_pack.schema.json": RealVideoBenchmarkPack.model_json_schema(),
        "bgm_beat_grid.schema.json": BgmBeatGrid.model_json_schema(),
        "bgm_candidate_ledger.schema.json": BgmCandidateLedger.model_json_schema(),
        "bgm_fit_plan.schema.json": BgmFitPlan.model_json_schema(),
        "bgm_rhythm_intelligence_report.schema.json": (
            BgmRhythmIntelligenceReport.model_json_schema()
        ),
        "bgm_recommendation_context.schema.json": BgmRecommendationContext.model_json_schema(),
        "bgm_recommendation_fit_review.schema.json": BgmRecommendationFitReview.model_json_schema(),
        "bgm_recommendation_selection.schema.json": BgmRecommendationSelection.model_json_schema(),
        "bgm_recommendation_set.schema.json": BgmRecommendationSet.model_json_schema(),
        "bgm_recommendation_validation_report.schema.json": (
            BgmRecommendationValidationReport.model_json_schema()
        ),
        "clip_score_record.schema.json": ClipScoreRecord.model_json_schema(),
        "composition_review.schema.json": CompositionReview.model_json_schema(),
        "creative_strategy_package.schema.json": CreativeStrategyPackage.model_json_schema(),
        "reframe_application.schema.json": ReframeApplication.model_json_schema(),
        "reframe_selection.schema.json": ReframeSelection.model_json_schema(),
        "editor_package.schema.json": EditorPackage.model_json_schema(),
        "editorial_score_set.schema.json": EditorialScoreSet.model_json_schema(),
        "edit_brief.schema.json": EditBrief.model_json_schema(),
        "evidence_map.schema.json": EvidenceMap.model_json_schema(),
        "fcpxml_draft.schema.json": FcpxmlDraft.model_json_schema(),
        "fcpxml_import_review.schema.json": FcpxmlImportReview.model_json_schema(),
        "fcpxml_import_review_candidate.schema.json": (
            FcpxmlImportReviewCandidate.model_json_schema()
        ),
        "fcpxml_repair_plan.schema.json": FcpxmlRepairPlan.model_json_schema(),
        "fcpxml_validation_report.schema.json": FcpxmlValidationReport.model_json_schema(),
        "final_export_manifest.schema.json": FinalExportManifest.model_json_schema(),
        "final_export_validation_report.schema.json": (
            FinalExportValidationReport.model_json_schema()
        ),
        "project_config.schema.json": ProjectConfig.model_json_schema(),
        "project_state.schema.json": ProjectState.model_json_schema(),
        "preview_render_manifest.schema.json": PreviewRenderManifest.model_json_schema(),
        "preview_validation_report.schema.json": PreviewValidationReport.model_json_schema(),
        "release_hardening_report.schema.json": ReleaseHardeningReport.model_json_schema(),
        "revision_plan.schema.json": RevisionPlan.model_json_schema(),
        "revision_application.schema.json": RevisionApplication.model_json_schema(),
        "revision_promotion.schema.json": RevisionPromotion.model_json_schema(),
        "nle_interchange_plan.schema.json": NleInterchangePlan.model_json_schema(),
        "operator_runbook.schema.json": OperatorRunbook.model_json_schema(),
        "edit_guidance_report.schema.json": EditGuidanceReport.model_json_schema(),
        "rhythm_agent_candidate.schema.json": RhythmAgentCandidate.model_json_schema(),
        "rhythm_intent.schema.json": RhythmIntent.model_json_schema(),
        "rhythm_media_qc_report.schema.json": RhythmMediaQcReport.model_json_schema(),
        "rhythm_plan.schema.json": RhythmPlan.model_json_schema(),
        "rhythm_repair_plan.schema.json": RhythmRepairPlan.model_json_schema(),
        "proposal_set.schema.json": ProposalSet.model_json_schema(),
        "proposal_context.schema.json": ProposalContext.model_json_schema(),
        "proposal_validation_report.schema.json": ProposalValidationReport.model_json_schema(),
        "source_record.schema.json": SourceRecord.model_json_schema(),
        "sound_decision.schema.json": SoundDecision.model_json_schema(),
        "style_template_package.schema.json": StyleTemplatePackage.model_json_schema(),
        "structure_recommendation.schema.json": StructureRecommendation.model_json_schema(),
        "text_timing_plan.schema.json": TextTimingPlan.model_json_schema(),
        "first_cut_self_review.schema.json": FirstCutSelfReview.model_json_schema(),
        "second_cut_render.schema.json": SecondCutRender.model_json_schema(),
        "second_cut_candidate.schema.json": SecondCutCandidate.model_json_schema(),
        "clip_record.schema.json": ClipRecord.model_json_schema(),
        "cut_review_report.schema.json": CutReviewReport.model_json_schema(),
        "keyframe_record.schema.json": KeyframeRecord.model_json_schema(),
        "transcript_record.schema.json": TranscriptRecord.model_json_schema(),
        "timeline_draft.schema.json": TimelineDraft.model_json_schema(),
        "timeline_validation_report.schema.json": TimelineValidationReport.model_json_schema(),
        "workflow_plan.schema.json": WorkflowPlan.model_json_schema(),
        "workflow_execution_record.schema.json": WorkflowExecutionRecord.model_json_schema(),
        "workflow_execution_review.schema.json": WorkflowExecutionReview.model_json_schema(),
    }
    for filename, schema in schemas.items():
        (output_dir / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
