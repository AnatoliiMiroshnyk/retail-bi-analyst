from datetime import date
import threading
import pandas as pd
import pytest
from PySide6.QtCore import QDate, Qt, QThread
from PySide6.QtWidgets import QFileDialog, QTableView
from src.core.application import prepare_view
from src.core.repository import SalesRepository
from src.core.data_loader import DataSourceConfig
from src.ui import ui_main_window as ui_module
from src.ui.ui_main_window import MainWindow


@pytest.fixture
def window(qtbot, monkeypatch, tmp_path):
    from src.ui.ui_settings import UiSettings
    monkeypatch.setattr(ui_module, 'load_settings', lambda: UiSettings())
    monkeypatch.setattr(ui_module, 'save_settings', lambda settings: None)
    w=MainWindow()
    w.errors=[]; w.infos=[]
    monkeypatch.setattr(w,'_show_error',w.errors.append)
    monkeypatch.setattr(w,'_show_info',w.infos.append)
    qtbot.addWidget(w)
    return w


def wait(window,qtbot):
    qtbot.waitUntil(lambda: not window._busy, timeout=20000)


def seed(window,sales):
    repo=SalesRepository(sales)
    window._commit_view(prepare_view(repo.raw), repo, None, True)
    return repo


def test_without_data_disabled_and_tables_readonly(window):
    assert not window.refresh_graph_btn.isEnabled()
    assert not window.save_graph_btn.isEnabled()
    assert not window.generate_report_action.isEnabled()
    for table in (window.data_table,window.kpi_table,window.rfm_table):
        assert table.editTriggers()==QTableView.EditTrigger.NoEditTriggers


def test_successful_import_date_sync_and_worker_thread(window,sales,tmp_path,qtbot,monkeypatch):
    path=tmp_path/'ok.csv'; sales.to_csv(path,index=False)
    real=ui_module.prepare_import
    worker_ids=[]; main=threading.get_ident(); gui_threads=[]
    def load(config):
        worker_ids.append(threading.get_ident())
        return real(config)
    real_commit=window._commit_view
    def commit(*args):
        gui_threads.append(QThread.currentThread()==window.thread())
        return real_commit(*args)
    monkeypatch.setattr(ui_module,'prepare_import',load)
    monkeypatch.setattr(window,'_commit_view',commit)
    window._load_dataframe_with_config(DataSourceConfig('csv',path))
    wait(window,qtbot)
    assert not window.errors
    assert worker_ids[0]!=main and gui_threads==[True]
    assert window.date_from_edit.date()==QDate(2026,1,1)
    assert window.date_to_edit.date()==QDate(2026,1,2)
    assert window._current_df.customer_id.iloc[0]=='001'


@pytest.mark.parametrize('stage',['schema','kpi','rfm','report'])
def test_import_failure_preserves_all_committed_state(window,sales,tmp_path,qtbot,monkeypatch,stage):
    seed(window,sales)
    window.category_combo.setCurrentIndex(window.category_combo.findData('A'))
    window._on_apply_filters(); wait(window,qtbot)
    assert len(window._current_df)==2
    assert window._current_filter.category=='A'
    old_repo=window._repo; old_filter=window._current_filter
    old_frame=window._current_df.copy(); old_controls=window._capture_controls()
    old_html=window.report_view.toHtml()
    new=sales.copy()
    path=tmp_path/'next.csv'
    if stage=='schema': new=new.drop(columns='sale_date')
    else:
        from src.core import application
        target={'kpi':'calculate_kpi_results','rfm':'calculate_rfm_results','report':'generate_markdown_report'}[stage]
        def fail(*args): raise ValueError('injected '+stage+' failure')
        monkeypatch.setattr(application,target,fail)
    new.to_csv(path,index=False)
    window._load_dataframe_with_config(DataSourceConfig('csv',path)); wait(window,qtbot)
    assert window.errors and not window.infos
    assert window._repo is old_repo and window._current_filter is old_filter
    pd.testing.assert_frame_equal(window._current_df,old_frame)
    assert window._capture_controls()==old_controls
    assert window.report_view.toHtml()==old_html


def test_ui_commit_failure_rolls_back(window,sales,monkeypatch):
    repo=seed(window,sales)
    old_frame=window._current_df.copy()
    old_controls=window._capture_controls()
    old_model=window.data_table.model()
    prepared=prepare_view(repo.raw.iloc[:1])
    def fail(): raise RuntimeError('preview failure')
    monkeypatch.setattr(window,'_update_report_preview',fail)
    with pytest.raises(RuntimeError):
        window._commit_view(prepared,repo,None,True)
    pd.testing.assert_frame_equal(window._current_df,old_frame)
    assert window.data_table.model() is old_model
    assert window._capture_controls()==old_controls


def test_reset_dates_final_day_reverse_range(window,sales,qtbot):
    seed(window,sales)
    window.date_from_edit.setDate(QDate(2026,1,2))
    window.date_to_edit.setDate(QDate(2026,1,2))
    window._on_apply_filters(); wait(window,qtbot)
    assert len(window._current_df)==2
    old_filter=window._current_filter
    window.date_from_edit.setDate(QDate(2026,1,3))
    window._on_apply_filters()
    assert window.errors
    assert len(window._current_df)==2 and window._current_filter is old_filter
    window._on_reset_filters(); wait(window,qtbot)
    assert len(window._current_df)==3 and window._current_filter is None
    assert window.date_from_edit.date()==QDate(2026,1,1)
    assert window.date_to_edit.date()==QDate(2026,1,2)
    assert window.category_combo.currentData() is None


@pytest.mark.parametrize('operation',['filter','reset'])
def test_filter_or_reset_calculation_failure_preserves_state(window,sales,qtbot,monkeypatch,operation):
    seed(window,sales)
    window.category_combo.setCurrentIndex(window.category_combo.findData('A'))
    window._on_apply_filters(); wait(window,qtbot)
    assert len(window._current_df)==2
    old_filter=window._current_filter
    old_frame=window._current_df.copy(); old_controls=window._capture_controls()
    def fail(*args): raise ValueError('injected calculation error')
    monkeypatch.setattr(ui_module,'prepare_view',fail)
    if operation=='filter':
        window.category_combo.setCurrentIndex(0)
        window._on_apply_filters()
    else: window._on_reset_filters()
    wait(window,qtbot)
    assert window.errors
    pd.testing.assert_frame_equal(window._current_df,old_frame)
    assert window._current_filter is old_filter
    assert window._capture_controls()==old_controls


def test_repository_filter_exception_is_handled(window,sales,qtbot,monkeypatch):
    seed(window,sales)
    previous=window._current_df.copy()
    def fail(*args): raise RuntimeError('filter error')
    monkeypatch.setattr(window._repo,'filtered',fail)
    window._on_apply_filters(); wait(window,qtbot)
    pd.testing.assert_frame_equal(window._current_df,previous)
    assert 'filter error' in window.errors[-1]


def test_graph_success_then_filter_empty_clears_and_cannot_save(window,sales,qtbot,tmp_path,monkeypatch):
    seed(window,sales)
    window._on_refresh_graph(); wait(window,qtbot)
    assert window._graph_png and window.save_graph_btn.isEnabled()
    path=tmp_path/'graph.png'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'PNG'))
    window._on_save_graph(); wait(window,qtbot)
    assert path.read_bytes().startswith(b'\x89PNG')
    window.min_total_spin.setValue(1000)
    window._on_apply_filters(); wait(window,qtbot)
    assert window._current_df.empty
    assert not window._graph_png and not window.graph_axes.images and not window.graph_axes.lines
    assert not window.refresh_graph_btn.isEnabled() and not window.save_graph_btn.isEnabled()
    window._on_save_graph()
    assert 'current graph' in window.errors[-1]


@pytest.mark.parametrize('operation',['reset','import','selection','theme'])
def test_graph_invalidated_on_every_change(window,sales,qtbot,tmp_path,operation):
    seed(window,sales)
    window._on_refresh_graph(); wait(window,qtbot)
    assert window.save_graph_btn.isEnabled()
    if operation=='reset': window._on_reset_filters(); wait(window,qtbot)
    elif operation=='import':
        path=tmp_path/'next.csv'; sales.to_csv(path,index=False)
        window._load_dataframe_with_config(DataSourceConfig('csv',path)); wait(window,qtbot)
    elif operation=='selection': window.graph_type_combo.setCurrentIndex(1)
    else: window._on_set_dark_theme()
    assert window._graph_png is None and not window.save_graph_btn.isEnabled()


def test_graph_failure_never_keeps_previous_result(window,sales,qtbot,monkeypatch):
    seed(window,sales)
    window._on_refresh_graph(); wait(window,qtbot)
    def fail(*args): raise RuntimeError('plot error')
    monkeypatch.setattr(ui_module,'build_graph',fail)
    window._on_refresh_graph(); wait(window,qtbot)
    assert window.errors and not window._graph_png and not window.save_graph_btn.isEnabled()
    assert not window.graph_axes.images


def test_numeric_datetime_sort_raw_roles_and_no_edit(window,sales):
    seed(window,sales)
    from src.ui.table_items import ValueItem
    from PySide6.QtGui import QStandardItemModel
    model=QStandardItemModel()
    for raw in [10.,2.,1000.]: model.appendRow(ValueItem(raw))
    model.sort(0)
    assert [model.item(i).data(Qt.ItemDataRole.UserRole) for i in range(3)]==[2.,10.,1000.]
    date_model=QStandardItemModel()
    for raw in [pd.Timestamp('2026-10-01'),pd.Timestamp('2025-12-31')]: date_model.appendRow(ValueItem(raw))
    date_model.sort(0)
    assert date_model.item(0).data(Qt.ItemDataRole.UserRole)==pd.Timestamp('2025-12-31')
    for table in [window.data_table,window.kpi_table,window.rfm_table]:
        model=table.model()
        assert not (model.flags(model.index(0,0)) & Qt.ItemFlag.ItemIsEditable)
    assert isinstance(window.kpi_table.model().item(0,1).data(Qt.ItemDataRole.UserRole),float)


@pytest.mark.parametrize('kind',['md','html','xlsx'])
@pytest.mark.parametrize('stage',['generation','writing'])
def test_report_errors_no_false_success_and_preserve_state(window,sales,qtbot,tmp_path,monkeypatch,kind,stage):
    seed(window,sales)
    before=window._current_df.copy()
    old_filter=window._current_filter
    path=tmp_path/('report.'+kind); path.write_bytes(b'OLD')
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'report'))
    def fail(*args,**kwargs): raise PermissionError('injected '+stage+' failure')
    if stage=='generation':
        name={'md':'generate_markdown_report','html':'generate_html_report','xlsx':'generate_excel_report'}[kind]
        monkeypatch.setattr(ui_module,name,fail)
    else:
        from src.reports import safety
        monkeypatch.setattr(safety.os,'replace',fail)
    window._export_report(kind); wait(window,qtbot)
    assert window.errors and not window.infos
    assert path.read_bytes()==b'OLD'
    assert window._current_filter is old_filter
    pd.testing.assert_frame_equal(window._current_df,before)
    assert list(tmp_path.iterdir())==[path]


@pytest.mark.parametrize('kind',['md','html','xlsx'])
def test_report_success(window,sales,qtbot,tmp_path,monkeypatch,kind):
    seed(window,sales)
    path=tmp_path/('report.'+kind)
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'report'))
    window._export_report(kind); wait(window,qtbot)
    assert path.exists() and path.stat().st_size>100
    assert window.infos and not window.errors


def test_close_while_worker_running_ignored(window,qtbot):
    from PySide6.QtGui import QCloseEvent
    import time
    window._run_task(lambda: time.sleep(.15),lambda result:None,'test')
    event=QCloseEvent(); window.closeEvent(event)
    assert not event.isAccepted()
    wait(window,qtbot)


def test_filter_combos_populated_and_customer_filter_works(window,sales,qtbot):
    seed(window,sales)
    assert window.category_combo.findData('A')>0
    assert window.customer_combo.findData('001')>0
    window.customer_combo.setCurrentIndex(window.customer_combo.findData('001'))
    window._on_apply_filters(); wait(window,qtbot)
    assert window._current_df.customer_id.tolist()==['001','001']
    window._on_reset_filters(); wait(window,qtbot)
    assert window.customer_combo.currentData() is None
    assert len(window._current_df)==3


def test_graph_write_failure_no_false_success(window,sales,qtbot,tmp_path,monkeypatch):
    seed(window,sales)
    window._on_refresh_graph(); wait(window,qtbot)
    path=tmp_path/'image.png'; path.write_bytes(b'OLD')
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'PNG'))
    from src.reports import safety
    def fail(*args): raise PermissionError('file locked')
    monkeypatch.setattr(safety.os,'replace',fail)
    window._on_save_graph(); wait(window,qtbot)
    assert path.read_bytes()==b'OLD'
    assert window.errors and not window.infos
    assert window.save_graph_btn.isEnabled()  # still valid; saving can be retried


def test_sqlite_import_dialog_dispatches_safe_reader(window,tmp_path,monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    path=tmp_path/'source.db'; path.touch()
    monkeypatch.setattr(QInputDialog,'getItem',lambda *a,**k:('SQLite',True))
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(path),'SQLite'))
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**k:('sales',True))
    monkeypatch.setattr(QInputDialog,'getMultiLineText',lambda *a,**k:('',True))
    configs=[]
    monkeypatch.setattr(window,'_load_dataframe_with_config',configs.append)
    window._on_import_sql_db()
    assert configs[0].source_type=='sqlite' and configs[0].path==path


def test_menu_actions_and_all_languages_keep_current_data(window,sales,qtbot):
    seed(window,sales)
    previous=window._current_df.copy()
    for language in ui_module.SUPPORTED_LANG_CODES:
        window._language_code=language
        window._apply_language()
        assert window.tabs.tabText(0)
    window._on_increase_font()
    window._on_decrease_font()
    window._on_set_light_theme()
    pd.testing.assert_frame_equal(window._current_df,previous)


def test_date_fields_do_not_silently_clamp_old_dates(window,sales,qtbot):
    sales['sale_date']=['1700-01-01','1700-01-02','1700-01-02 23:59:59']
    seed(window,sales)
    assert window.date_from_edit.date()==QDate(1700,1,1)
    assert window.date_to_edit.date()==QDate(1700,1,2)
    window._on_apply_filters(); wait(window,qtbot)
    assert len(window._current_df)==3


def test_commit_failure_restores_previous_successful_graph(window,sales,qtbot,monkeypatch):
    repo=seed(window,sales)
    window._on_refresh_graph(); wait(window,qtbot)
    old_png=window._graph_png; old_revision=window._revision
    def fail(): raise RuntimeError('render failed')
    monkeypatch.setattr(window,'_update_report_preview',fail)
    with pytest.raises(RuntimeError): window._commit_view(prepare_view(repo.raw.iloc[:1]),repo,None,True)
    assert window._graph_png==old_png and window._graph_revision==old_revision
    assert window.save_graph_btn.isEnabled()
    assert len(window.graph_axes.images)==1


def test_commit_graph_controls_failure_restores_snapshot(window,sales,qtbot,monkeypatch):
    repo=seed(window,sales)
    window._on_refresh_graph(); wait(window,qtbot)
    old_png=window._graph_png
    old_choices=[window.graph_data_combo.itemText(i) for i in range(window.graph_data_combo.count())]
    previous=window._current_df.copy()
    def fail(): raise RuntimeError('graph controls failed')
    monkeypatch.setattr(window,'_refresh_graph_controls',fail)
    with pytest.raises(RuntimeError): window._commit_view(prepare_view(repo.raw.iloc[:1]),repo,None,True)
    assert old_png==window._graph_png and window.save_graph_btn.isEnabled()
    assert [window.graph_data_combo.itemText(i) for i in range(window.graph_data_combo.count())]==old_choices
    pd.testing.assert_frame_equal(window._current_df,previous)


def test_thread_start_failure_restores_enabled_state(window,sales,monkeypatch):
    seed(window,sales)
    previous=window._current_df.copy()
    def fail(*args): raise RuntimeError('cannot allocate thread')
    monkeypatch.setattr(ui_module.TaskThread,'start',fail)
    window._on_reset_filters()
    assert not window._busy and window.centralWidget().isEnabled()
    assert window.errors and window._task is None
    pd.testing.assert_frame_equal(window._current_df,previous)


def test_real_data_table_sorting_uses_raw_values(window,sales):
    seed(window,sales)
    model=window.data_table.model()
    total=list(window._current_df.columns).index('total_price')
    window.data_table.sortByColumn(total,Qt.SortOrder.AscendingOrder)
    assert [model.item(i,total).data(Qt.ItemDataRole.UserRole) for i in range(model.rowCount())]==[2.,10.,12.]
    dates=list(window._current_df.columns).index('sale_date')
    window.data_table.sortByColumn(dates,Qt.SortOrder.DescendingOrder)
    actual=[model.item(i,dates).data(Qt.ItemDataRole.UserRole) for i in range(model.rowCount())]
    assert actual==sorted(actual,reverse=True)


def test_failed_import_also_preserves_unapplied_visible_controls(window,sales,tmp_path,qtbot):
    seed(window,sales)
    window.category_combo.setCurrentIndex(window.category_combo.findData('B'))
    window.date_from_edit.setDate(QDate(2026,1,2))
    visible_before=window._capture_controls()
    path=tmp_path/'invalid.csv'; path.write_text('bad\n1\n')
    window._load_dataframe_with_config(DataSourceConfig('csv',path)); wait(window,qtbot)
    assert window._capture_controls()==visible_before
    assert window._current_filter is None and len(window._current_df)==3


@pytest.mark.parametrize('kind',['excel','json','sqlite'])
def test_all_import_sources_through_window(window,sales,tmp_path,qtbot,kind):
    import json,sqlite3
    path=tmp_path/('source.'+{'excel':'xlsx','json':'json','sqlite':'db'}[kind])
    if kind=='excel': sales.to_excel(path,index=False)
    elif kind=='json': path.write_text(json.dumps(sales.to_dict('records')),encoding='utf-8')
    else:
        with sqlite3.connect(path) as connection: sales.to_sql('sales',connection,index=False)
    config=DataSourceConfig(kind,path,table_name='sales' if kind=='sqlite' else None)
    window._load_dataframe_with_config(config); wait(window,qtbot)
    assert not window.errors
    assert len(window._current_df)==3
    assert window._current_df.customer_id.tolist()==['001','002','001']


def test_visible_graph_selection_restored_on_commit_failure(window,sales,qtbot,monkeypatch):
    repo=seed(window,sales)
    window.graph_data_combo.setCurrentIndex(2)
    window.graph_type_combo.setCurrentIndex(1)
    window._on_refresh_graph(); wait(window,qtbot)
    before=(window.graph_data_combo.currentText(),window.graph_type_combo.currentText(),window._graph_png)
    def fail(): raise RuntimeError('preview error')
    monkeypatch.setattr(window,'_update_report_preview',fail)
    with pytest.raises(RuntimeError): window._commit_view(prepare_view(repo.raw.iloc[:1]),repo,None,True)
    assert (window.graph_data_combo.currentText(),window.graph_type_combo.currentText(),window._graph_png)==before
