**Table 1. NEU-DET dataset and splits (per class; identical counts for seeds 0, 1, 2)**

| Class | Train | Validation | Locked test | Total |
|---|---|---|---|---|
| crazing | 180 | 60 | 60 | 300 |
| inclusion | 180 | 60 | 60 | 300 |
| patches | 180 | 60 | 60 | 300 |
| pitted surface | 180 | 60 | 60 | 300 |
| rolled-in scale | 180 | 60 | 60 | 300 |
| scratches | 180 | 60 | 60 | 300 |
| Total | 1080 | 360 | 360 | 1800 |

*Train/validation = group-blocked split of the 1,440 NEU-DET train-folder images (group-blocked (blocks of 20 indices), 3 val blocks/class); locked test = the 360 NEU-DET validation-folder images, read once per frozen model.*
