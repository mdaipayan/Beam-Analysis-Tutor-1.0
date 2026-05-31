"""
utils/session.py
================
Central session-state manager for BeamEdu.

Streamlit reruns the whole script on every interaction, so all persistent
state (beam configuration, load list, computed results, quiz progress) is kept
in st.session_state.  This module wraps that store with typed helper functions
so the pages never touch raw dict keys directly.

Usage
-----
    from utils.session import S
    S.init()                       # call once at the top of every page
    S.set_beam(beam)
    beam   = S.get_beam()
    S.add_load(PointLoad(3.0, 10.0))
    loads  = S.get_loads()
    S.solve()                      # runs the engine, caches reactions + sfd/bmd
"""

from __future__ import annotations

import hashlib
import uuid
from typing import List, Optional

import streamlit as st

from engine import (
    Beam, AnyLoad,
    solve_reactions, compute_sfd_bmd,
    ReactionResult, SFDBMDResult,
)


# Default keys
_KEYS = {
    "student_id":   None,
    "beam":         None,    # Beam object
    "beam_label":   "",      # human description for display
    "loads":        [],      # list[AnyLoad]
    "reactions":    None,    # ReactionResult
    "sfdbmd":       None,    # SFDBMDResult
    "solved":       False,   # whether current beam+loads have been solved
    "quiz_pre":     None,    # pre-test score (0-100)
    "quiz_post":    None,    # post-test score (0-100)
    "quiz_history": [],      # list of attempt dicts
    "last_error":   "",      # latest recoverable solve/validation error
}


class _Session:
    """Thin wrapper around st.session_state with typed helpers."""

    # ── Initialisation ────────────────────────────────────────────────
    def init(self) -> None:
        """Initialise all session keys (idempotent — safe to call every rerun)."""
        for key, default in _KEYS.items():
            if key not in st.session_state:
                # Use a fresh copy for mutable defaults
                st.session_state[key] = list(default) if isinstance(default, list) else default
        if st.session_state["student_id"] is None:
            st.session_state["student_id"] = str(uuid.uuid4())[:8]

    # ── Student ID ─────────────────────────────────────────────────────
    @property
    def student_id(self) -> str:
        return st.session_state.get("student_id", "anon")

    def set_student_id(self, sid: str) -> None:
        """Store only an 8-character pseudonymous code, never the raw typed ID."""
        clean = (sid or "anon").strip()
        st.session_state["student_id"] = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:8]

    # ── Beam ───────────────────────────────────────────────────────────
    def set_beam(self, beam: Beam, label: str = "") -> None:
        st.session_state["beam"]       = beam
        st.session_state["beam_label"] = label
        self._invalidate()

    def get_beam(self) -> Optional[Beam]:
        return st.session_state.get("beam")

    @property
    def beam_label(self) -> str:
        return st.session_state.get("beam_label", "")

    # ── Loads ──────────────────────────────────────────────────────────
    def add_load(self, load: AnyLoad) -> None:
        self._validate_load_for_current_beam(load)
        st.session_state["loads"].append(load)
        self._invalidate()

    def remove_load(self, index: int) -> None:
        loads = st.session_state["loads"]
        if 0 <= index < len(loads):
            loads.pop(index)
            self._invalidate()

    def clear_loads(self) -> None:
        st.session_state["loads"] = []
        self._invalidate()

    def get_loads(self) -> List[AnyLoad]:
        return st.session_state.get("loads", [])

    # ── Solving ────────────────────────────────────────────────────────
    def solve(self) -> bool:
        """
        Run the engine on the current beam + loads.
        Caches ReactionResult and SFDBMDResult in session.
        Returns True on success, False if no beam/loads configured.
        """
        beam  = self.get_beam()
        loads = self.get_loads()
        st.session_state["last_error"] = ""
        if beam is None:
            st.session_state["last_error"] = "Create or load a beam first."
            return False
        if len(loads) == 0:
            st.session_state["last_error"] = "Add at least one load before solving."
            return False

        try:
            for load in loads:
                self._validate_load_for_current_beam(load)
            rxn = solve_reactions(beam, loads)
            res = compute_sfd_bmd(beam, rxn.reactions, loads)
        except Exception as exc:
            st.session_state["last_error"] = str(exc)
            return False

        st.session_state["reactions"] = rxn
        st.session_state["sfdbmd"]    = res
        st.session_state["solved"]    = True
        return True

    @property
    def is_solved(self) -> bool:
        return st.session_state.get("solved", False)

    @property
    def last_error(self) -> str:
        return st.session_state.get("last_error", "")

    def get_reactions(self) -> Optional[ReactionResult]:
        return st.session_state.get("reactions")

    def get_sfdbmd(self) -> Optional[SFDBMDResult]:
        return st.session_state.get("sfdbmd")

    # ── Quiz ───────────────────────────────────────────────────────────
    def set_quiz_score(self, phase: str, score: float) -> None:
        """phase = 'pre' or 'post'."""
        key = f"quiz_{phase}"
        st.session_state[key] = score

    def get_quiz_score(self, phase: str) -> Optional[float]:
        return st.session_state.get(f"quiz_{phase}")

    def log_quiz_attempt(self, attempt: dict) -> None:
        st.session_state["quiz_history"].append(attempt)

    @property
    def quiz_history(self) -> list:
        return st.session_state.get("quiz_history", [])

    # ── Internal ───────────────────────────────────────────────────────
    def _invalidate(self) -> None:
        """Mark cached results stale when beam or loads change."""
        st.session_state["solved"]    = False
        st.session_state["reactions"] = None
        st.session_state["sfdbmd"]    = None

    def _validate_load_for_current_beam(self, load: AnyLoad) -> None:
        """Reject loads that do not fit inside the active beam span."""
        beam = self.get_beam()
        if beam is None:
            raise ValueError("Create or load a beam before adding loads.")

        L = float(beam.length)
        eps = 1e-9

        def _check_position(x: float, label: str) -> None:
            if x < -eps or x > L + eps:
                raise ValueError(f"{label} at x = {x:.3f} m is outside the beam span 0–{L:.3f} m.")

        if hasattr(load, "position"):
            _check_position(float(load.position), "Load")
        else:
            start = float(load.start)
            end = float(load.end)
            _check_position(start, "Load start")
            _check_position(end, "Load end")
            if start >= end:
                raise ValueError("Distributed load start must be less than its end position.")


# Singleton instance used across all pages
S = _Session()
