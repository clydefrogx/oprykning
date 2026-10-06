# oprykning

A small web page that shows who moves up ("rykker op") in Herre Senior 4 7:7 Efterår. It reads the standings of 8 pools from dbu.dk and ranks the teams across all pools. The page is rebuilt three times a day and published with GitHub Pages.

## Run it locally

```
pip install requests beautifulsoup4
python build.py
```

Then open `site/index.html` in a browser. The script prints `Wrote site/index.html with N teams` when it works.

## Publish with GitHub Pages

1. In the repository, go to Settings, then Pages, and set Source to "GitHub Actions".
2. Go to the Actions tab, pick "Update dashboard" and press "Run workflow".
3. The page appears at `https://<username>.github.io/oprykning/`.

After that it updates by itself (see `.github/workflows/update.yml`).
