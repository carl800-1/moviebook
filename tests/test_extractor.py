import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extractor.movie_extractor import MovieExtractor


def test_extract_candidates():
    extractor = MovieExtractor(use_tmdb=False)

    text1 = "今天看了《奥本海默》太炸了"
    candidates1 = extractor.extract_candidates(text1)
    assert "奥本海默" in candidates1, f"Expected in {candidates1}"
    print(f"OK book title: {candidates1}")

    text2 = "推荐《流浪地球2》和《满江红》"
    candidates2 = extractor.extract_candidates(text2)
    assert "流浪地球2" in candidates2
    assert "满江红" in candidates2
    print(f"OK multi titles: {candidates2}")

    print("All tests passed!")


async def test_normalize():
    extractor = MovieExtractor(use_tmdb=False)
    results = await extractor.extract_and_normalize([
        "今天看了《奥本海默》",
        "推荐《流浪地球2》",
    ])
    print(f"Normalize result: {results}")
    await extractor.close()


if __name__ == "__main__":
    test_extract_candidates()
    asyncio.run(test_normalize())
