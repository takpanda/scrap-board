"""
統合テスト: 管理画面にPostprocess Jobs Dashboardへのリンクが追加されていることを確認
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """テストクライアントのフィクスチャ"""
    return TestClient(app)


def test_admin_page_contains_jobs_dashboard_link(client):
    """
    管理画面(/admin)のHTMLレスポンスにジョブダッシュボードへのリンクが含まれることを検証
    Requirements: 1.1, 1.2
    """
    response = client.get("/admin")
    assert response.status_code == 200

    html_content = response.text

    # ジョブダッシュボードへのリンクが存在することを確認
    assert 'href="/admin/postprocess_jobs"' in html_content, \
        "管理画面にジョブダッシュボードへのリンク(href)が含まれていません"


def test_admin_page_link_has_accessibility_attributes(client):
    """
    リンクに適切なアクセシビリティ属性(aria-label, title)が含まれることを検証
    Requirements: 3.2
    """
    response = client.get("/admin")
    assert response.status_code == 200

    html_content = response.text

    # aria-label属性が存在することを確認
    assert 'aria-label="Postprocess Jobs Dashboard へ移動"' in html_content, \
        "aria-label属性が含まれていません"

    # title属性が存在することを確認
    assert 'title="ジョブダッシュボード"' in html_content, \
        "title属性が含まれていません"


def test_admin_page_link_has_icon(client):
    """
    リンクにLucide Iconsのactivityアイコンが含まれることを検証
    Requirements: 1.4
    """
    response = client.get("/admin")
    assert response.status_code == 200

    html_content = response.text

    # Lucide Icons のactivityアイコンが存在することを確認
    assert 'data-lucide="activity"' in html_content, \
        "Lucide Iconsのactivityアイコンが含まれていません"


def test_admin_page_link_has_label_text(client):
    """
    リンクに「ジョブダッシュボード」というテキストラベルが含まれることを検証
    Requirements: 2.3
    """
    response = client.get("/admin")
    assert response.status_code == 200

    html_content = response.text

    # テキストラベル「ジョブダッシュボード」が存在することを確認
    assert 'ジョブダッシュボード' in html_content, \
        "リンクに「ジョブダッシュボード」というテキストが含まれていません"


def test_admin_page_template_renders_without_errors(client):
    """
    テンプレート修正後もページが正常にレンダリングされることを確認
    Requirements: 4.1, 4.2
    """
    response = client.get("/admin")

    # 200 OKレスポンスを確認
    assert response.status_code == 200, \
        f"管理画面のレンダリングに失敗しました: {response.status_code}"

    # HTMLが空でないことを確認
    assert len(response.text) > 0, \
        "レスポンスが空です"

    # 基本的なHTMLタグが含まれることを確認
    assert '<html' in response.text.lower(), \
        "有効なHTMLドキュメントではありません"
