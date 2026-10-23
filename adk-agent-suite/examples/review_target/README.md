# Intentionally faulty review fixture

The three flaws in `app.py` are deliberate: a DFS container bug, SQL interpolation,
and a shell invocation. Its regression suite should report one error and one failure.
The project-level test suite separately verifies that the assistant reports these.
Only this operator-controlled fixture is executed in trusted demo mode.
