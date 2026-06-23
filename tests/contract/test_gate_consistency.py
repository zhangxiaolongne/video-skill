from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_current_gate_is_proposal_execution_authorization_gate_across_primary_docs():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    master = (ROOT / "artist_portrait_editor_revision5_optimized.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    vision = (ROOT / "docs" / "VISION.md").read_text(encoding="utf-8")
    progress = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")
    v010i = (ROOT / "docs" / "V0_010I_PROPOSAL_EXECUTION_AUTHORIZATION_GATE.md").read_text(
        encoding="utf-8"
    )

    assert "Current gate: V0-010i proposal execution authorization gate only." in agents
    assert "V0-010i 提案 execution authorization 闸门" in master
    assert "Current V0-010i proposal execution authorization gate work" in readme
    assert "Current implementation gate: V0-010i proposal execution authorization gate only." in vision
    assert "Current local gate: V0-010i proposal execution authorization gate only" in progress
    assert "V0-010i opens deterministic provider execution authorization packets" in v010i


def test_current_gate_forbids_future_media_and_creative_surfaces():
    docs = "\n".join(
        [
            (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "V0_010A_PROPOSAL_READINESS_GATE.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "docs" / "V0_010B_PROPOSAL_CONTEXT_GATE.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "docs" / "V0_010C_TEXT_MODEL_GATE.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "docs" / "V0_010D_PROPOSAL_VALIDATION_GATE.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "docs" / "V0_010E_PROPOSAL_REQUEST_GATE.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "docs" / "V0_010F_PROPOSAL_ADAPTER_PREFLIGHT_GATE.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "docs" / "V0_010G_PROPOSAL_PROVIDER_REGISTRY_GATE.md").read_text(
                encoding="utf-8"
            ),
            (
                ROOT / "docs" / "V0_010H_PROPOSAL_PROVIDER_RESULT_ENVELOPE_GATE.md"
            ).read_text(encoding="utf-8"),
            (
                ROOT / "docs" / "V0_010I_PROPOSAL_EXECUTION_AUTHORIZATION_GATE.md"
            ).read_text(encoding="utf-8"),
        ]
    )

    assert "OpenCV" in docs
    assert "BGM selection" in docs
    assert "timeline generation" in docs
    assert "preview rendering" in docs
    assert "model calls" in docs
    assert "network search" in docs
    assert "image generation or image editing" in docs
    assert "fake proposals" in docs
    assert "full creative proposal generation" in docs


def test_stage_a_acceptance_is_historical_not_active_gate():
    content = (ROOT / "docs" / "STAGE_A_ACCEPTANCE.md").read_text(encoding="utf-8")

    assert "accepted historical engineering foundation" in content
    assert "Stage A is no longer the active implementation gate" in content
    assert "V0-003 media scan foundation" in content


def test_v003_release_readiness_records_local_validation_scope():
    content = (ROOT / "docs" / "V0_003_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, not pushed, not tagged." in content
    assert "b003a91 Record release readiness checkpoint" in content
    assert "gate reconciliation from Stage A-only" in content
    assert "deterministic `output/scan_report.md`" in content
    assert "downstream map/review invalidation" in content
    assert "pytest: 74 passed, 1 skipped" in content
    assert "run_checks.py: checks passed" in content


def test_v004_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_004_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "6760831 Close V0-003 media scan foundation" in content
    assert "`ClipRecord` schema" in content
    assert "deterministic fixed-window segmentation" in content
    assert "canonical `.artist-portrait/data/clips.jsonl`" in content
    assert "pytest: 79 passed, 1 skipped" in content
    assert "run_checks.py: checks passed" in content


def test_v005_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_005_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`features.scene_detection` routing" in content
    assert "Optional PySceneDetect adapter" in content
    assert "`pyscenedetect` clip method" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v006_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_006_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`TranscriptRecord` Pydantic model" in content
    assert "`artist-portrait transcribe --project`" in content
    assert "local-only faster-whisper adapter" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v007_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_007_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`KeyframeRecord` Pydantic model" in content
    assert "`artist-portrait keyframes --project`" in content
    assert "rebuildable `.artist-portrait/cache/keyframes/`" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v008_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_008_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`AnalysisRecord` Pydantic model" in content
    assert "`artist-portrait analyze --project`" in content
    assert "Evidence-only aggregation" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v009_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_009_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`map` now requires current `.artist-portrait/data/analysis.jsonl`" in content
    assert "priority review queue" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010a_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010A_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalSet` Pydantic model" in content
    assert "`propose` readiness command" in content
    assert "No fake `proposals.json` or `proposals.md` generation" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010b_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010B_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalContext` Pydantic model" in content
    assert "Deterministic `.artist-portrait/data/proposal_context.json`" in content
    assert "No fake `proposals.json` or `proposals.md` generation" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010c_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010C_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`TextModelGate` Pydantic model" in content
    assert "Deterministic `.artist-portrait/data/text_model_gate.json`" in content
    assert "No fake `proposals.json` or `proposals.md` generation" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010d_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010D_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalValidationReport` Pydantic model" in content
    assert "Canonical `.artist-portrait/data/proposal_validation.json`" in content
    assert "Rebuildable `output/proposal_review.md`" in content
    assert "BGM strategy fields" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010e_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010E_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalRequestPacket` Pydantic model" in content
    assert "Canonical `.artist-portrait/data/proposal_request.json`" in content
    assert "Blocked and ready proposal request packet states" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010f_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010F_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalAdapterCheck` Pydantic model" in content
    assert "Canonical `.artist-portrait/data/proposal_adapter_check.json`" in content
    assert "Plaintext secret material detection" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010g_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010G_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalProviderRegistry` Pydantic model" in content
    assert "`ProposalMockAdapterHandshake` Pydantic model" in content
    assert "Canonical `.artist-portrait/data/proposal_provider_registry.json`" in content
    assert "Canonical `.artist-portrait/data/proposal_mock_adapter_handshake.json`" in content
    assert "no proposal content generation" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010h_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010H_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalProviderResultEnvelope` Pydantic model" in content
    assert "Canonical `.artist-portrait/data/proposal_provider_result.json`" in content
    assert "`payload_generated: false`" in content
    assert "`validation_performed: false`" in content
    assert "`proposal_content_generated: false`" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content


def test_v010i_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_010I_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "`ProposalExecutionAuthorization` Pydantic model" in content
    assert "Canonical `.artist-portrait/data/proposal_execution_authorization.json`" in content
    assert "`approved_execution_gate: false`" in content
    assert "`user_approval_present: false`" in content
    assert "`execution_performed: false`" in content
    assert "`proposal_content_generated: false`" in content
    assert "pytest:" in content
    assert "run_checks.py:" in content
