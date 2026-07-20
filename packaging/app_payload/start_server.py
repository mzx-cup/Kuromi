import os, sys
os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import uvicorn
import main
if __name__ == '__main__':
    uvicorn.run(main.app, host='127.0.0.1', port=8000, log_level='warning')
