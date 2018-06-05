from datasetplus import DatasetPlus
import rank
import threading
import time
from sys import version_info
if version_info.major == 2:
    import Tkinter as tk
    import ttk
    from tkFileDialog import askopenfilename
    import tkMessageBox as messagebox
elif version_info.major == 3:
    import tkinter as tk
    from tkinter import ttk
    from tkinter.filedialog import askopenfilename
    from tkinter import messagebox


class RankingPage(tk.Frame):
    def __init__(self, parent, **kwargs):
        super(RankingPage, self).__init__(parent, **kwargs)
        self.parent = parent
        self.nb_label = 'Ranking'
        self.roi_filename = None
        row_i = -1

        # page contents
        # 1 select mask
        #   instruction label
        row_i += 1
        tk.Label(self, text='Select an ROI mask:') \
            .grid(row=row_i, column=0, padx=10, pady=(10, 2), sticky='w')
        #   browse button
        row_i += 1
        tk.Button(self,
                  command=self.get_filename_from_button,
                  text=' Browse ',
                  highlightthickness=0) \
            .grid(row=row_i, column=0, padx=10, pady=(2, 10))
        #   file name label
        self.label_filename = tk.Label(self, text='', width=20)
        self.label_filename.grid(row=row_i, column=1, padx=(0, 10), sticky='w')

        # 2 select image
        #   instruction label
        row_i += 1
        tk.Label(self, text='Rank terms by:') \
            .grid(row=row_i, column=0, padx=10, pady=(10, 2), sticky='w')
        #   radio buttons
        self.image_labels = {
            'Forward inference with a uniform prior=0.5': 'pAgF_given_pF=0.50',
            'Forward inference z score (consistency)': 'consistency_z',
            'Forward inference with multiple comparisons correction (FDR=0.01)': 'pAgF_z_FDR_0.01',
            'Reverse inference with a uniform prior=0.5': 'pFgA_given_pF=0.50',
            'Reverse inference z score (specificity)': 'specificity_z',
            'Reverse inference with multiple comparisons correction (FDR=0.01)': 'pFgA_z_FDR_0.01'
        }
        self.img_var = tk.StringVar(value='pFgA_given_pF=0.50')
        for text in self.image_labels.keys():
            row_i += 1
            tk.Radiobutton(self,
                           text=text,
                           variable=self.img_var,
                           value=self.image_labels[text]) \
                .grid(row=row_i, column=0, columnspan=2, padx=30, sticky='w')

        # 3 select procedure
        #   instruction label
        row_i += 1
        tk.Label(self, text='Procedure:') \
            .grid(row=row_i, column=0, padx=10, pady=(10, 2), sticky='w')
        #   radio buttons
        self.proc_var = tk.BooleanVar(value=False)  # whether to rank first
        for i, text in enumerate(['Average the values across ROI first, then rank terms',
                                  'Rank terms at each voxel first, then average ranks across ROI']):
            row_i += 1
            tk.Radiobutton(self,
                           text=text,
                           variable=self.proc_var,
                           value=bool(i)) \
                .grid(row=row_i, column=0, columnspan=2, padx=30, sticky='w')

        # 4 run button
        row_i += 1
        self.btn_file = tk.Button(self,
                                  command=self.run,
                                  text=' Start Ranking ',
                                  highlightthickness=0)
        self.btn_file.grid(row=row_i, columnspan=2, padx=1, pady=10)

    def get_filename_from_button(self):
        self.roi_filename = askopenfilename(initialdir='./',
                                            title='Select mask file',
                                            filetypes=(('NIFTI files', '*.nii'),
                                                       ('NIFTI files', '*.nii.gz'),
                                                       ('all files', '*.*')))
        self.label_filename.config(text=self.roi_filename.split('/')[-1])

    def run(self):
        if self.roi_filename is None:
            no_roi = messagebox.askyesno('Warning', 'You didn\'t specify an ROI file. '
                                                    'Are you sure you want to continue?')
            if not no_roi:
                return
        else:
            # load ROI mask to database
            if not Global().update_status('Loading ROI...', user_op=True):
                return
            th = threading.Thread(target=Global().dataset.mask, args=[self.roi_filename])
            th.start()
            th.join()
        if not Global().update_status('Ranking terms...', user_op=(self.roi_filename is None)):
            return
        selected_img = self.img_var.get()
        selected_proc = self.proc_var.get()
        out_filename = '/Users/mengdu/Repos/neurosynthExtension/test_rank.csv'  # TODO
        rank.rank(Global().dataset, rank_by=selected_img, rank_first=selected_proc,
                  csv_name=out_filename)
        Global().update_status('Done. A file is saved to ' + out_filename)


class _Singleton(type):
    """
    Metaclass for singletons. See https://stackoverflow.com/a/6798042/3290263
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(_Singleton('SingletonMeta', (object,), {})): pass


class Global(Singleton):
    """
    A class that maintains the NeuroSynth dataset instance and the current app status
    """
    def __init__(self, parent, **kwargs):
        self.status = 'Ready'
        self.has_error = False
        self.history = []
        self.dataset = None
        self.status_mutex = threading.Lock()

        # GUI
        self.statusbar = tk.Frame(parent, **kwargs)
        self.text_width = 80
        self.statusbar_label = tk.Label(parent, text=self.status.ljust(self.text_width),
                                        bd=1, relief=tk.SUNKEN, anchor='w',  padx=3,
                                        font=('Menlo', 12), bg='#6d6d6d', fg='#d6d6d6')
        self.statusbar_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _update_status(self, status, is_error=False):  # not thread safe
        self.status = status
        self.has_error = is_error
        self.history.append(status)
        if len(status) > self.text_width:
            statusbar_text = status[:(self.text_width - 3)] + '...'
        else:
            statusbar_text = status.ljust(self.text_width)
        text_color = '#ff0000' if is_error else '#d6d6d6'
        self.statusbar_label.config(text=statusbar_text, fg=text_color)

    def update_status(self, status='Ready', is_error=False, user_op=False):  # thread safe
        """
        :param status: string
        :param is_error: (boolean) the text will show as red if True
        :param user_op: (boolean) whether a status change is requested by user.
                        If True and the current status is not 'Ready', the request will
                        be declined, in which case this function returns False and the
                        status bar shows a warning
        :return: (boolean) whether the status has been updated successfully
        """
        prev = False
        with self.status_mutex:
            if (not user_op) or self.is_ready():
                self._update_status(status, is_error)
            else:
                prev = self.status, self.has_error
                self._update_status('Still running the last task... Please try again later',
                                    is_error=True)

        def back_to_prev(prev_status, prev_has_error):
            time.sleep(2)
            with self.status_mutex:
                if not self.is_ready():  # last task still running
                    self._update_status(prev_status, is_error=prev_has_error)

        if prev:
            th = threading.Thread(target=back_to_prev, args=prev)
            th.start()

        return not bool(prev)

    def is_ready(self):
        return self.status == 'Ready'

    def load_pkl_database(self):
        """
        Call this function after a Status has been initiated
        :param data_file: (string) path to a pickled data file
        """
        self.update_status('Loading database...')
        self.dataset = DatasetPlus.load_default_database()
        self.update_status()


class MainApp(tk.Frame):
    def __init__(self, parent, **kwargs):
        super(MainApp, self).__init__(parent, **kwargs)
        self.parent = parent

        parent.title('NeuroSynth+')
        # parent.geometry('350x200')

        # notebook layout
        self.notebook = ttk.Notebook(parent)
        self.nb_pages = [RankingPage(self.notebook)]
        for page in self.nb_pages:
            self.notebook.add(page, text=page.nb_label)
        self.notebook.pack(expand=1, fill='both')


def main():
    # try:
    root = tk.Tk()
    main_app = MainApp(root)
    main_app.pack(side='top', fill='both')
    Global(root)
    # load NeuroSynth database in another thread
    th = threading.Thread(target=Global.load_pkl_database, args=[Global()])
    th.start()
    root.mainloop()
    # except Exception as e:
    #     if status is None:
    #         messagebox.showerror('Error', str(e))
    #     else:
    #         status.update_status(str(e), is_error=True)


if __name__ == '__main__':
    main()