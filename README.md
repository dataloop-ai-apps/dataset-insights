Build script

```bash

# or even more succinctly
bazel build tensorboard -- --logdir path/to/logs
```

Development script

```bash

# or even more succinctly
ibazel run tensorboard:dev -- --logdir path/to/logs --host 0.0.0.0 --port 3000
```
