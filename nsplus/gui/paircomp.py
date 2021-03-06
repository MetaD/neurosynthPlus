from __future__ import absolute_import, print_function
from .globals import Global
from .pagebuilder import PageBuilder
from .autocompletepage import AutocompletePage
from ..src.comparison import compare_expressions
from threading import Thread


class PairCompPage(PageBuilder, AutocompletePage):
    def __init__(self, parent, **kwargs):
        super(PairCompPage, self).__init__(parent=parent, **kwargs)
        self.parent = parent
        self.nb_label = 'Pairwise Comparison'
        row_i = -1

        # page contents
        #  first expression
        row_i += 1
        self.ac_entry1 = self.create_labeled_ac_entry(row=row_i)[0]

        #  second expression
        row_i += 2
        self.ac_entry2 = self.create_labeled_ac_entry(
            row=row_i,
            label_text='Enter term or expression in contrast:')[0]

        self.add_comparison_settings(row=row_i + 2, start_func=self.start)

    def start(self):
        if not Global().validate_settings():
            return

        # get variables
        expr = self.ac_entry1.get().strip()
        contrary_expr = self.ac_entry2.get().strip()
        exclude_overlap = self.overlap_var.get() == 1
        reduce = self.equal_size_var.get() == 1
        two_way = self.two_way_var.get() == 1
        num_iterations = Global().num_iterations if reduce else 1

        mask = ('mask', Global().roi_filename or Global().default_roi)

        # discard any unsaved change
        self.entry_control(entry=self.entry_num_iter, button=self.btn_num_iter,
                           entry_val=num_iterations, discard_change=True)

        if not Global().update_status(
                status='Comparing "%s" and "%s"...' % (expr, contrary_expr),
                is_ready=False, user_op=True):
            return

        if (not Global().validate_expression(expr)) or \
                (not Global().validate_expression(contrary_expr)):
            return

        def _compare():
            try:
                # run
                compare_expressions(Global().dataset, expr, contrary_expr, exclude_overlap,
                                    reduce, num_iterations, two_way,
                                    fdr=Global().fdr,
                                    extra_info=[mask],
                                    outpath=Global().outpath)

                Global().root.event_generate('<<Done_pair_comp>>')  # trigger event

            except Exception as e:
                Global().show_error(e)

        Thread(target=_compare).start()
        Global().root.bind('<<Done_pair_comp>>',
                           lambda e: Global().update_status(
                               status='Done. Files are saved to ' + Global().outpath,
                               is_ready=True))
