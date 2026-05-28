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
        st.session_state["student_id"] = sid

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
        if beam is None or len(loads) == 0:
            return False

        rxn = solve_reactions(beam, loads)
        res = compute_sfd_bmd(beam, rxn.reactions, loads)

        st.session_state["reactions"] = rxn
        st.session_state["sfdbmd"]    = res
        st.session_state["solved"]    = True
        return True

    @property
    def is_solved(self) -> bool:
        return st.session_state.get("solved", False)

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


# Singleton instance used across all pages
S = _Session()
