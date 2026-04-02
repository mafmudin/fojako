# Evaluation Dataset

## Project Selection Criteria

- Open-source Android/Kotlin projects
- Diverse scale: small (<50 files), medium (50-200), large (200+)
- Diverse patterns: data classes, DI (Hilt/Dagger), coroutines, Compose UI, MVVM/MVI
- Well-maintained with clear architecture

## Projects

| # | Project | Repo | Size | Key Patterns |
|---|---------|------|------|-------------|
| 1 | Now in Android | [android/nowinandroid](https://github.com/android/nowinandroid) | Large | Compose, Hilt, coroutines, MVVM, multi-module |
| 2 | Tivi | [chrisbanes/tivi](https://github.com/chrisbanes/tivi) | Large | Compose, Circuit, SQLDelight, multi-module |
| 3 | Compose Samples | [android/compose-samples](https://github.com/android/compose-samples) | Large | Compose UI, various architectures |
| 4 | Sunflower | [android/sunflower](https://github.com/android/sunflower) | Small | Room, WorkManager, MVVM |
| 5 | Architecture Components Samples | [android/architecture-components-samples](https://github.com/android/architecture-components-samples) | Medium | LiveData, ViewModel, Room, Paging |

## Setup

Clone all projects into `~/evaluation-datasets/`:

```bash
mkdir -p ~/evaluation-datasets
cd ~/evaluation-datasets

git clone --depth 1 https://github.com/android/nowinandroid.git
git clone --depth 1 https://github.com/chrisbanes/tivi.git
git clone --depth 1 https://github.com/android/compose-samples.git
git clone --depth 1 https://github.com/android/sunflower.git
git clone --depth 1 https://github.com/android/architecture-components-samples.git
```

## Notes

- Use `--depth 1` for shallow clones (we only need current source, not git history)
- Only `.kt` and `.java` files under `src/main/` are relevant; test and generated files are auto-skipped by kotlin-mcp
