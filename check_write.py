import tempfile, os
print("tempdir:", tempfile.gettempdir())
print("home:", os.path.expanduser("~"))
test = os.path.join(os.path.expanduser("~"), "DN_dataset_test")
os.makedirs(test, exist_ok=True)
print("created:", test)
