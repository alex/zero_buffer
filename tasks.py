from invoke import task, run


@task
def release(version):
    """
    Version should be a string like '0.4' or '1.0'
    """
    run('git tag -s "{}"'.format(version))
    run('python setup.py sdist')
    run('twine upload -s dist/zero_buffer-{}*'.format(version))
