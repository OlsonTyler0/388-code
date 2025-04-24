# ╔═══════════════════════════════════════════════════════════╗
#   main routes
#       This file routes all traffic from the following routes:
#       - /
#       - /more
# ╚═══════════════════════════════════════════════════════════╝
from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET'])
def homepage():
    return render_template('homepage.html')

@main_bp.route('/more', methods=['GET'])
@login_required
def more():
    return render_template('more.html')