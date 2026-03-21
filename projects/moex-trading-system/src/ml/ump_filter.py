"""UMP (Umpire) Trade Filter — ML-based trade blocker.

Inspired by bbfamily/abu UmpBu system (GPL-3 — formulas only, code from scratch).

UMP does NOT generate signals. It BLOCKS bad trades before execution
by comparing them to historical patterns of winning/losing trades.

Two judges work independently:

1. MainUmp (GMM): Clusters historical trades via Gaussian Mixture Models.
   Identifies "toxic" clusters where >65% of trades were losses.
   New trade hitting a toxic cluster → BLOCKED.

2. EdgeUmp (kNN+Correlation): Two-pass similarity search:
   Pass 1: Euclidean distance → fast rejection of distant trades
   Pass 2: Pearson correlation → structural similarity check
   Asymmetric voting with golden ratio (0.618) thresholds.

Usage:
    ump = UmpireFilter()
    ump.fit(historical_trades_features, historical_trades_pnl)

    # Before executing a new trade:
    verdict = ump.judge(new_trade_features)
    if verdict.blocked:
        print(f"BLOCKED: {verdict.reason}")
    else:
        execute_trade()
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


class Verdict(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class UmpireResult:
    """Result from the umpire system.

    Attributes:
        verdict: PASS / BLOCK / UNCERTAIN.
        blocked: True if trade should be blocked.
        main_vote: MainUmp vote (True = block).
        edge_vote: EdgeUmp vote (+1 = win, -1 = loss, 0 = uncertain).
        confidence: How confident the umpire is [0, 1].
        reason: Human-readable explanation.
    """

    verdict: Verdict
    blocked: bool
    main_vote: bool
    edge_vote: int
    confidence: float
    reason: str


class MainUmp:
    """GMM-based trade filter — identifies toxic clusters.

    Trains multiple GMMs with different n_components.
    For each: finds clusters where loss_rate > threshold.
    New trade blocked if it lands in a toxic cluster in enough models.

    Args:
        n_components_range: Range of GMM components to try.
        loss_threshold: Min loss rate to mark cluster as toxic (default 0.65).
        min_hits: Min number of models that must flag the trade (default 3).
    """

    def __init__(
        self,
        n_components_range: tuple[int, int] = (10, 40),
        loss_threshold: float = 0.65,
        min_hits: int = 3,
    ) -> None:
        self._range = n_components_range
        self._loss_threshold = loss_threshold
        self._min_hits = min_hits
        self._models: list[tuple[GaussianMixture, set[int]]] = []
        self._scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train GMMs on historical trade features.

        Args:
            X: Feature matrix (n_trades, n_features).
            y: Binary labels: 1 = win, 0 = loss.
        """
        X_scaled = self._scaler.fit_transform(X)
        self._models.clear()

        for k in range(self._range[0], self._range[1] + 1, 5):
            if k > len(X_scaled):
                break
            try:
                gmm = GaussianMixture(
                    n_components=k, covariance_type="full",
                    max_iter=200, random_state=42, n_init=1,
                )
                gmm.fit(X_scaled)
                clusters = gmm.predict(X_scaled)

                # Find toxic clusters
                toxic: set[int] = set()
                for c in range(k):
                    mask = clusters == c
                    if mask.sum() < 3:
                        continue
                    loss_rate = 1.0 - y[mask].mean()
                    if loss_rate >= self._loss_threshold:
                        toxic.add(c)

                if toxic:
                    self._models.append((gmm, toxic))
            except Exception:
                continue

        self._fitted = True

    def predict(self, x: np.ndarray) -> tuple[bool, int, int]:
        """Check if trade features hit toxic clusters.

        Args:
            x: Feature vector (1D or 2D with 1 row).

        Returns:
            (is_blocked, n_hits, n_models)
        """
        if not self._fitted or not self._models:
            return False, 0, 0

        x_scaled = self._scaler.transform(x.reshape(1, -1))
        hits = 0
        for gmm, toxic in self._models:
            cluster = gmm.predict(x_scaled)[0]
            if cluster in toxic:
                hits += 1

        return hits >= self._min_hits, hits, len(self._models)


class EdgeUmp:
    """kNN + Correlation similarity-based trade filter.

    Two-pass algorithm:
    1. Euclidean distance → reject if too far from any historical trade
    2. Pearson correlation → find structurally similar trades
    3. Asymmetric voting with golden ratio thresholds

    Args:
        n_neighbors: Number of nearest neighbors to consider.
        dist_threshold: Max euclidean distance to consider (default 0.668).
        corr_threshold: Min Pearson correlation to count (default 0.91).
        golden_ratio: Voting asymmetry (default 0.618).
    """

    # Golden ratio thresholds for asymmetric classification
    PHI = 0.618
    PHI_COMPLEMENT = 0.236  # 1 - 0.618 * (1 + sqrt(5))/2... simplified: 1-2*0.382

    def __init__(
        self,
        n_neighbors: int = 100,
        dist_threshold: float = 0.668,
        corr_threshold: float = 0.91,
    ) -> None:
        self._n_neighbors = n_neighbors
        self._dist_threshold = dist_threshold
        self._corr_threshold = corr_threshold
        self._X: np.ndarray | None = None
        self._labels: np.ndarray | None = None  # +1, 0, -1
        self._scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train on historical trades.

        Args:
            X: Feature matrix.
            y: PnL values (positive = win, negative = loss).
        """
        self._X = self._scaler.fit_transform(X)
        n = len(y)

        # Tri-class labeling via golden ratio
        ranks = np.argsort(np.argsort(y))  # rank 0..n-1
        labels = np.zeros(n, dtype=int)
        top_win_threshold = n * (1 - self.PHI_COMPLEMENT)
        top_loss_threshold = n * self.PHI_COMPLEMENT
        labels[ranks >= top_win_threshold] = 1   # top winners
        labels[ranks < top_loss_threshold] = -1   # top losers
        self._labels = labels
        self._fitted = True

    def predict(self, x: np.ndarray) -> tuple[int, float]:
        """Judge a new trade.

        Args:
            x: Feature vector.

        Returns:
            (vote, confidence): vote = +1 (win), -1 (loss/block), 0 (uncertain).
        """
        if not self._fitted or self._X is None:
            return 0, 0.0

        x_scaled = self._scaler.transform(x.reshape(1, -1))

        # Pass 1: Euclidean distances
        dists = np.sqrt(((self._X - x_scaled) ** 2).sum(axis=1))
        min_dist = dists.min()
        if min_dist > self._dist_threshold:
            return 0, 0.0  # too far from any precedent

        # Top-K nearest
        k = min(self._n_neighbors, len(dists))
        nearest_idx = np.argpartition(dists, k)[:k]

        # Pass 2: Pearson correlation with nearest neighbors
        win_score = 0.0
        loss_score = 0.0
        for idx in nearest_idx:
            corr = np.corrcoef(x_scaled.flatten(), self._X[idx])[0, 1]
            if np.isnan(corr) or abs(corr) < self._corr_threshold:
                continue
            similarity = abs(corr)
            label = self._labels[idx]
            if label == 1:
                win_score += similarity
            elif label == -1:
                loss_score += similarity

        # Asymmetric voting with golden ratio
        if win_score * self.PHI > loss_score and win_score > 0:
            confidence = min(win_score / (win_score + loss_score + 1e-10), 1.0)
            return 1, confidence
        elif loss_score * self.PHI > win_score and loss_score > 0:
            confidence = min(loss_score / (win_score + loss_score + 1e-10), 1.0)
            return -1, confidence
        return 0, 0.0


class UmpireFilter:
    """Combined Main + Edge umpire filter.

    Both judges must agree to block. If only one blocks → UNCERTAIN.

    Args:
        main_kwargs: Parameters for MainUmp.
        edge_kwargs: Parameters for EdgeUmp.
    """

    def __init__(
        self,
        main_kwargs: dict | None = None,
        edge_kwargs: dict | None = None,
    ) -> None:
        self._main = MainUmp(**(main_kwargs or {}))
        self._edge = EdgeUmp(**(edge_kwargs or {}))
        self._fitted = False

    def fit(
        self, X: np.ndarray, pnl: np.ndarray,
    ) -> None:
        """Train both umpires.

        Args:
            X: Trade feature matrix (n_trades, n_features).
            pnl: PnL per trade (positive = win).
        """
        y_binary = (pnl > 0).astype(float)
        self._main.fit(X, y_binary)
        self._edge.fit(X, pnl)
        self._fitted = True

    def judge(self, x: np.ndarray) -> UmpireResult:
        """Judge a potential trade.

        Args:
            x: Feature vector for the new trade.

        Returns:
            UmpireResult with verdict and reasoning.
        """
        if not self._fitted:
            return UmpireResult(
                Verdict.PASS, False, False, 0, 0.0, "Not fitted"
            )

        main_blocked, main_hits, main_total = self._main.predict(x)
        edge_vote, edge_conf = self._edge.predict(x)

        # Decision logic
        if main_blocked and edge_vote == -1:
            verdict = Verdict.BLOCK
            blocked = True
            confidence = min((main_hits / max(main_total, 1)) * 0.5 + edge_conf * 0.5, 1.0)
            reason = (
                f"BLOCKED by both judges: "
                f"MainUmp={main_hits}/{main_total} toxic clusters, "
                f"EdgeUmp=LOSS (conf={edge_conf:.2f})"
            )
        elif main_blocked or edge_vote == -1:
            verdict = Verdict.UNCERTAIN
            blocked = False
            confidence = 0.3
            parts = []
            if main_blocked:
                parts.append(f"MainUmp blocked ({main_hits}/{main_total})")
            if edge_vote == -1:
                parts.append(f"EdgeUmp=LOSS (conf={edge_conf:.2f})")
            reason = f"UNCERTAIN: {', '.join(parts)}"
        else:
            verdict = Verdict.PASS
            blocked = False
            confidence = edge_conf if edge_vote == 1 else 0.5
            reason = (
                f"PASS: MainUmp clear, "
                f"EdgeUmp={'WIN' if edge_vote == 1 else 'neutral'}"
            )

        return UmpireResult(
            verdict=verdict,
            blocked=blocked,
            main_vote=main_blocked,
            edge_vote=edge_vote,
            confidence=round(confidence, 4),
            reason=reason,
        )
