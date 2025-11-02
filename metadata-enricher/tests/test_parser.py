import pytest
from metadata_enricher.enricher import parse_filename

# Casos de teste parametrizados para a função parse_filename
@pytest.mark.parametrize("filename, expected", [
    # --- Casos de Séries ---
    ("Power.Rangers.S01E01.mkv", {'type': 'series', 'title': 'Power Rangers', 'season': 1, 'episode': 1}),
    ("game.of.thrones.s08e06.1080p.bluray.x264-strife.mkv", {'type': 'series', 'title': 'game of thrones', 'season': 8, 'episode': 6}),
    ("The_Mandalorian.S02E08.WEB-DL.DDP5.1.H.264-NOSiDE.mkv", {'type': 'series', 'title': 'The_Mandalorian', 'season': 2, 'episode': 8}),
    ("Mr.Robot.S04E13.Final.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTb.mkv", {'type': 'series', 'title': 'Mr.Robot', 'season': 4, 'episode': 13}),

    # --- Casos de Filmes ---
    ("The.Matrix.1999.1080p.mkv", {'type': 'movie', 'title': 'The Matrix', 'year': 1999}),
    ("Avengers.Endgame.2019.BluRay.DDP5.1.x264-HiFi.mkv", {'type': 'movie', 'title': 'Avengers Endgame', 'year': 2019}),
    ("Inception (2010) 1080p BRRip.mp4", {'type': 'movie', 'title': 'Inception', 'year': 2010}),
    ("2001 A Space Odyssey 1968.mkv", {'type': 'movie', 'title': '2001 A Space Odyssey', 'year': 1968}),

    # --- Casos Edge/Fallback ---
    ("My Awesome Home Video.mov", {'type': 'movie', 'title': 'My Awesome Home Video', 'year': None}),
    ("Commercial_Ad_Nike.mp4", {'type': 'movie', 'title': 'Commercial_Ad_Nike', 'year': None}),
    ("ArquivoSemExtensao", {'type': 'movie', 'title': 'ArquivoSemExtensao', 'year': None}),
    ("S01E01.Orphan.Black.mkv", {'type': 'movie', 'title': 'S01E01 Orphan Black', 'year': None}), # Deve falhar a regex de série
])
def test_parse_filename(filename, expected):
    """
    Testa a função parse_filename com uma variedade de formatos de nome de arquivo.
    """
    assert parse_filename(filename) == expected

def test_parse_filename_empty_string():
    """
    Testa a função parse_filename com uma string vazia.
    """
    assert parse_filename("") == {'type': 'movie', 'title': '', 'year': None}
