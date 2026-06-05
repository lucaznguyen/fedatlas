from __future__ import annotations

import pandas as pd

from .utils import canonical_repo_url, extract_arxiv_id, normalize_doi, normalize_title, parse_github_url, title_similarity


def _prep_pwc(pwc_papers: pd.DataFrame) -> pd.DataFrame:
    if pwc_papers.empty:
        return pd.DataFrame()
    df = pwc_papers.copy()
    if "arxiv_id" in df.columns:
        df["arxiv_id"] = df["arxiv_id"].fillna(df.get("paper_url", pd.Series(index=df.index)).map(extract_arxiv_id))
    elif "paper_url" in df.columns:
        df["arxiv_id"] = df["paper_url"].map(extract_arxiv_id)
    else:
        df["arxiv_id"] = pd.NA
    for source_col in ["doi", "url_abs", "url_pdf"]:
        if source_col in df.columns:
            df["arxiv_id"] = df["arxiv_id"].fillna(df[source_col].map(extract_arxiv_id))
    title_col = "title" if "title" in df.columns else "paper_title"
    df["title_norm"] = df[title_col].map(normalize_title) if title_col in df.columns else ""
    df["doi_norm"] = df["doi"].map(normalize_doi) if "doi" in df.columns else None
    df["pwc_title"] = df[title_col] if title_col in df.columns else None
    df["pwc_paper_id"] = df["id"] if "id" in df.columns else df.get("paper_url")
    return df


def match_papers_with_code(papers: pd.DataFrame, pwc_papers: pd.DataFrame, pwc_links: pd.DataFrame) -> pd.DataFrame:
    if papers.empty or pwc_papers.empty or pwc_links.empty:
        return pd.DataFrame(columns=["work_id", "pwc_paper_id", "pwc_title", "repo_url", "repo_owner", "repo_name", "is_official", "match_method", "match_confidence", "source_method"])
    pwc = _prep_pwc(pwc_papers)
    links = pwc_links.copy()
    if "paper_id" not in links.columns and "paper_url" in links.columns:
        links["paper_id"] = links["paper_url"]
    if "paper_arxiv_id" in links.columns:
        links["paper_arxiv_id_norm"] = links["paper_arxiv_id"].astype("string").str.lower()
    else:
        links["paper_arxiv_id_norm"] = pd.NA
    repo_col = "repo_url" if "repo_url" in links.columns else "repository_url"
    links_by_id = {key: group for key, group in links.dropna(subset=["paper_id"]).groupby("paper_id", sort=False)}
    links_by_url = {key: group for key, group in links.dropna(subset=["paper_url"]).groupby("paper_url", sort=False)} if "paper_url" in links.columns else {}
    links_by_arxiv = {key: group for key, group in links.dropna(subset=["paper_arxiv_id_norm"]).groupby("paper_arxiv_id_norm", sort=False)}
    matches: list[dict[str, object]] = []
    pwc_by_doi = {r["doi_norm"]: r for _, r in pwc.dropna(subset=["doi_norm"]).iterrows() if r["doi_norm"]}
    pwc_by_arxiv = {r["arxiv_id"]: r for _, r in pwc.dropna(subset=["arxiv_id"]).iterrows() if r["arxiv_id"]}
    pwc_by_title = {r["title_norm"]: r for _, r in pwc.iterrows() if r.get("title_norm")}
    paper_rows: list[tuple[object, pd.Series, str, list[str]]] = []
    needed_tokens: set[str] = set()
    for _, paper in papers.iterrows():
        title_norm = normalize_title(paper.get("title"))
        tokens = [t for t in title_norm.split() if len(t) > 5]
        paper_rows.append((paper.get("work_id"), paper, title_norm, tokens))
        needed_tokens.update(tokens)

    token_index: dict[str, list[int]] = {token: [] for token in needed_tokens}
    if needed_tokens:
        for idx, title_norm in pwc["title_norm"].dropna().items():
            for token in set(str(title_norm).split()).intersection(needed_tokens):
                token_index[token].append(idx)

    for _, paper, title_norm, tokens in paper_rows:
        match = None
        method = None
        confidence = 0.0
        doi = normalize_doi(paper.get("doi"))
        arxiv = paper.get("arxiv_id") or extract_arxiv_id(paper.get("doi_url"), paper.get("title"))
        if doi and doi in pwc_by_doi:
            match = pwc_by_doi[doi]
            method = "doi_exact"
            confidence = 1.0
        elif arxiv and arxiv in pwc_by_arxiv:
            match = pwc_by_arxiv[arxiv]
            method = "arxiv_exact"
            confidence = 1.0
        elif title_norm and title_norm in pwc_by_title:
            match = pwc_by_title[title_norm]
            method = "title_exact"
            confidence = 0.98
        else:
            # Narrow fuzzy matching to candidates sharing at least one uncommon token.
            indexed_tokens = [token for token in tokens if token_index.get(token)]
            if indexed_tokens:
                rarest_token = min(indexed_tokens, key=lambda token: len(token_index[token]))
                subset = pwc.loc[token_index[rarest_token][:200]]
                best_row = None
                best_score = 0.0
                for _, candidate in subset.iterrows():
                    score = title_similarity(title_norm, candidate.get("title_norm"))
                    if score > best_score:
                        best_score = score
                        best_row = candidate
                if best_row is not None and best_score >= 0.94:
                    match = best_row
                    method = "title_fuzzy"
                    confidence = best_score
        if match is None:
            continue
        pwc_id = match.get("pwc_paper_id")
        paper_url = match.get("paper_url")
        match_arxiv = match.get("arxiv_id")
        link_frames = []
        if pwc_id in links_by_id:
            link_frames.append(links_by_id[pwc_id])
        if paper_url in links_by_url:
            link_frames.append(links_by_url[paper_url])
        if match_arxiv and match_arxiv in links_by_arxiv:
            link_frames.append(links_by_arxiv[match_arxiv])
        if not link_frames:
            continue
        paper_links = pd.concat(link_frames, ignore_index=True).drop_duplicates()
        for _, link in paper_links.iterrows():
            repo_url = link.get(repo_col)
            owner, repo = parse_github_url(repo_url)
            if not owner or not repo:
                continue
            matches.append({
                "work_id": paper.get("work_id"),
                "pwc_paper_id": pwc_id,
                "pwc_title": match.get("pwc_title"),
                "repo_url": canonical_repo_url(owner, repo),
                "repo_owner": owner,
                "repo_name": repo,
                "is_official": link.get("is_official"),
                "match_method": method,
                "match_confidence": confidence,
                "source_method": "paperswithcode_dump",
            })
    return pd.DataFrame(matches).drop_duplicates() if matches else pd.DataFrame(columns=["work_id", "pwc_paper_id", "pwc_title", "repo_url", "repo_owner", "repo_name", "is_official", "match_method", "match_confidence", "source_method"])
