import * as React from 'react';
import { Dialog, showDialog, showErrorMessage } from '@jupyterlab/apputils';
import { IRenderMimeRegistry } from '@jupyterlab/rendermime';
import { ISettingRegistry } from '@jupyterlab/settingregistry';
import { Menu } from '@lumino/widgets';
import { GitExtension } from '../model';
import { hiddenButtonStyle } from '../style/ActionButtonStyle';
import { fileListWrapperClass } from '../style/FileListStyle';
import { Git } from '../tokens';
import { openListedFile } from '../utils';
import { ActionButton } from './ActionButton';
import { isDiffSupported } from './diff/Diff';
import { openDiffView } from './diff/DiffWidget';
import { ISpecialRef } from './diff/model';
import { FileItem } from './FileItem';
import { GitStage } from './GitStage';

export namespace CommandIDs {
  export const gitFileOpen = 'git:context-open';
  export const gitFileUnstage = 'git:context-unstage';
  export const gitFileStage = 'git:context-stage';
  export const gitFileTrack = 'git:context-track';
  export const gitFileDiscard = 'git:context-discard';
  export const gitFileDiffWorking = 'git:context-diffWorking';
  export const gitFileDiffIndex = 'git:context-diffIndex';
}

export interface IFileListState {
  selectedFile: Git.IStatusFile | null;
}

export interface IFileListProps {
  files: Git.IStatusFile[];
  model: GitExtension;
  renderMime: IRenderMimeRegistry;
  settings: ISettingRegistry.ISettings;
}

export class FileList extends React.Component<IFileListProps, IFileListState> {
  constructor(props: IFileListProps) {
    super(props);

    const commands = this.props.model.commands;
    this._contextMenuStaged = new Menu({ commands });
    this._contextMenuUnstaged = new Menu({ commands });
    this._contextMenuUntracked = new Menu({ commands });

    this.state = {
      selectedFile: null
    };

    if (!commands.hasCommand(CommandIDs.gitFileOpen)) {
      commands.addCommand(CommandIDs.gitFileOpen, {
        label: 'Open',
        caption: 'Open selected file',
        execute: async () => {
          await openListedFile(this.state.selectedFile, this.props.model);
        }
      });
    }

    if (!commands.hasCommand(CommandIDs.gitFileDiffWorking)) {
      commands.addCommand(CommandIDs.gitFileDiffWorking, {
        label: 'Diff',
        caption: 'Diff selected file',
        execute: async () => {
          await openDiffView(
            this.state.selectedFile.to,
            this.props.model,
            {
              currentRef: { specialRef: 'WORKING' },
              previousRef: { gitRef: 'HEAD' }
            },
            this.props.renderMime
          );
        }
      });
    }

    if (!commands.hasCommand(CommandIDs.gitFileDiffIndex)) {
      commands.addCommand(CommandIDs.gitFileDiffIndex, {
        label: 'Diff',
        caption: 'Diff selected file',
        execute: async () => {
          await openDiffView(
            this.state.selectedFile.to,
            this.props.model,
            {
              currentRef: { specialRef: 'INDEX' },
              previousRef: { gitRef: 'HEAD' }
            },
            this.props.renderMime
          );
        }
      });
    }

    if (!commands.hasCommand(CommandIDs.gitFileStage)) {
      commands.addCommand(CommandIDs.gitFileStage, {
        label: 'Stage',
        caption: 'Stage the changes of selected file',
        execute: () => {
          this.addFile(this.state.selectedFile.to);
        }
      });
    }

    if (!commands.hasCommand(CommandIDs.gitFileTrack)) {
      commands.addCommand(CommandIDs.gitFileTrack, {
        label: 'Track',
        caption: 'Start tracking selected file',
        execute: () => {
          this.addFile(this.state.selectedFile.to);
        }
      });
    }

    if (!commands.hasCommand(CommandIDs.gitFileUnstage)) {
      commands.addCommand(CommandIDs.gitFileUnstage, {
        label: 'Unstage',
        caption: 'Unstage the changes of selected file',
        execute: () => {
          if (this.state.selectedFile.x !== 'D') {
            this.resetStagedFile(this.state.selectedFile.to);
          }
        }
      });
    }

    if (!commands.hasCommand(CommandIDs.gitFileDiscard)) {
      commands.addCommand(CommandIDs.gitFileDiscard, {
        label: 'Discard',
        caption: 'Discard recent changes of selected file',
        execute: () => {
          this.discardChanges(this.state.selectedFile.to);
        }
      });
    }

    [
      CommandIDs.gitFileOpen,
      CommandIDs.gitFileUnstage,
      CommandIDs.gitFileDiffIndex
    ].forEach(command => {
      this._contextMenuStaged.addItem({ command });
    });

    [
      CommandIDs.gitFileOpen,
      CommandIDs.gitFileStage,
      CommandIDs.gitFileDiscard,
      CommandIDs.gitFileDiffWorking
    ].forEach(command => {
      this._contextMenuUnstaged.addItem({ command });
    });

    [CommandIDs.gitFileOpen, CommandIDs.gitFileTrack].forEach(command => {
      this._contextMenuUntracked.addItem({ command });
    });
  }

  /** Handle right-click on a staged file */
  contextMenuStaged = (event: React.MouseEvent) => {
    event.preventDefault();
    this._contextMenuStaged.open(event.clientX, event.clientY);
  };

  /** Handle right-click on an unstaged file */
  contextMenuUnstaged = (event: React.MouseEvent) => {
    event.preventDefault();
    this._contextMenuUnstaged.open(event.clientX, event.clientY);
  };

  /** Handle right-click on an untracked file */
  contextMenuUntracked = (event: React.MouseEvent) => {
    event.preventDefault();
    this._contextMenuUntracked.open(event.clientX, event.clientY);
  };

  /** Reset all staged files */
  resetAllStagedFiles = async () => {
    await this.props.model.reset();
  };

  /** Reset a specific staged file */
  resetStagedFile = async (file: string) => {
    await this.props.model.reset(file);
  };

  /** Add all unstaged files */
  addAllUnstagedFiles = async () => {
    await this.props.model.addAllUnstaged();
  };

  /** Discard changes in all unstaged files */
  discardAllUnstagedFiles = async () => {
    const result = await showDialog({
      title: 'Discard all changes',
      body: `Are you sure you want to permanently discard changes to all files? This action cannot be undone.`,
      buttons: [Dialog.cancelButton(), Dialog.warnButton({ label: 'Discard' })]
    });
    if (result.button.accept) {
      try {
        await this.props.model.checkout();
      } catch (reason) {
        showErrorMessage('Discard all unstaged changes failed.', reason);
      }
    }
  };

  /** Discard changes in all unstaged and staged files */
  discardAllChanges = async () => {
    const result = await showDialog({
      title: 'Discard all changes',
      body: `Are you sure you want to permanently discard changes to all files? This action cannot be undone.`,
      buttons: [Dialog.cancelButton(), Dialog.warnButton({ label: 'Discard' })]
    });
    if (result.button.accept) {
      try {
        await this.props.model.resetToCommit();
      } catch (reason) {
        showErrorMessage('Discard all changes failed.', reason);
      }
    }
  };

  /** Add a specific unstaged file */
  addFile = async (...file: string[]) => {
    await this.props.model.add(...file);
  };

  /** Discard changes in a specific unstaged or staged file */
  discardChanges = async (file: string) => {
    const result = await showDialog({
      title: 'Discard changes',
      body: `Are you sure you want to permanently discard changes to ${file}? This action cannot be undone.`,
      buttons: [Dialog.cancelButton(), Dialog.warnButton({ label: 'Discard' })]
    });
    if (result.button.accept) {
      try {
        await this.props.model.reset(file);
        await this.props.model.checkout({ filename: file });
      } catch (reason) {
        showErrorMessage(`Discard changes for ${file} failed.`, reason, [
          Dialog.warnButton({ label: 'DISMISS' })
        ]);
      }
    }
  };

  /** Add all untracked files */
  addAllUntrackedFiles = async () => {
    await this.props.model.addAllUntracked();
  };

  addAllMarkedFiles = async () => {
    await this.addFile(...this.markedFiles.map(file => file.to));
  };

  updateSelectedFile = (file: Git.IStatusFile | null) => {
    this.setState({ selectedFile: file });
  };

  get markedFiles() {
    return this.props.files.filter(file => this.props.model.getMark(file.to));
  }

  render() {
    if (this.props.settings.composite['simpleStaging']) {
      return (
        <div className={fileListWrapperClass}>
          {this._renderSimpleStage(this.props.files)}
        </div>
      );
    } else {
      const stagedFiles: Git.IStatusFile[] = [];
      const unstagedFiles: Git.IStatusFile[] = [];
      const untrackedFiles: Git.IStatusFile[] = [];

      this.props.files.forEach(file => {
        switch (file.status) {
          case 'staged':
            stagedFiles.push(file);
            break;
          case 'unstaged':
            unstagedFiles.push(file);
            break;
          case 'untracked':
            untrackedFiles.push(file);
            break;

          default:
            break;
        }
      });

      return (
        <div
          className={fileListWrapperClass}
          onContextMenu={event => event.preventDefault()}
        >
          {this._renderStaged(stagedFiles)}
          {this._renderChanged(unstagedFiles)}
          {this._renderUntracked(untrackedFiles)}
        </div>
      );
    }
  }

  private _isSelectedFile(candidate: Git.IStatusFile): boolean {
    if (this.state.selectedFile === null) {
      return false;
    }

    return (
      this.state.selectedFile.x === candidate.x &&
      this.state.selectedFile.y === candidate.y &&
      this.state.selectedFile.from === candidate.from &&
      this.state.selectedFile.to === candidate.to
    );
  }

  private _renderStaged(files: Git.IStatusFile[]) {
    return (
      <GitStage
        actions={
          <ActionButton
            className={hiddenButtonStyle}
            disabled={files.length === 0}
            iconName={'git-remove'}
            title={'Unstage all changes'}
            onClick={this.resetAllStagedFiles}
          />
        }
        collapsible
        heading={'Staged'}
        nFiles={files.length}
      >
        {files.map((file: Git.IStatusFile) => {
          return (
            <FileItem
              key={file.to}
              actions={
                <React.Fragment>
                  {this._createDiffButton(file.to, 'INDEX')}
                  <ActionButton
                    className={hiddenButtonStyle}
                    iconName={'git-remove'}
                    title={'Unstage this change'}
                    onClick={() => {
                      this.resetStagedFile(file.to);
                    }}
                  />
                </React.Fragment>
              }
              file={file}
              contextMenu={this.contextMenuStaged}
              model={this.props.model}
              selected={this._isSelectedFile(file)}
              selectFile={this.updateSelectedFile}
            />
          );
        })}
      </GitStage>
    );
  }

  private _renderChanged(files: Git.IStatusFile[]) {
    const disabled = files.length === 0;
    return (
      <GitStage
        actions={
          <React.Fragment>
            <ActionButton
              className={hiddenButtonStyle}
              disabled={disabled}
              iconName={'git-discard'}
              title={'Discard All Changes'}
              onClick={this.discardAllUnstagedFiles}
            />
            <ActionButton
              className={hiddenButtonStyle}
              disabled={disabled}
              iconName={'git-add'}
              title={'Stage all changes'}
              onClick={this.addAllUnstagedFiles}
            />
          </React.Fragment>
        }
        collapsible
        heading={'Changed'}
        nFiles={files.length}
      >
        {files.map((file: Git.IStatusFile) => {
          return (
            <FileItem
              key={file.to}
              actions={
                <React.Fragment>
                  <ActionButton
                    className={hiddenButtonStyle}
                    iconName={'git-discard'}
                    title={'Discard changes'}
                    onClick={() => {
                      this.discardChanges(file.to);
                    }}
                  />
                  {this._createDiffButton(file.to, 'WORKING')}
                  <ActionButton
                    className={hiddenButtonStyle}
                    iconName={'git-add'}
                    title={'Stage this change'}
                    onClick={() => {
                      this.addFile(file.to);
                    }}
                  />
                </React.Fragment>
              }
              file={file}
              contextMenu={this.contextMenuUnstaged}
              model={this.props.model}
              selected={this._isSelectedFile(file)}
              selectFile={this.updateSelectedFile}
            />
          );
        })}
      </GitStage>
    );
  }

  private _renderUntracked(files: Git.IStatusFile[]) {
    return (
      <GitStage
        actions={
          <ActionButton
            className={hiddenButtonStyle}
            disabled={files.length === 0}
            iconName={'git-add'}
            title={'Track all untracked files'}
            onClick={this.addAllUntrackedFiles}
          />
        }
        collapsible
        heading={'Untracked'}
        nFiles={files.length}
      >
        {files.map((file: Git.IStatusFile) => {
          return (
            <FileItem
              key={file.to}
              actions={
                <ActionButton
                  className={hiddenButtonStyle}
                  iconName={'git-add'}
                  title={'Track this file'}
                  onClick={() => {
                    this.addFile(file.to);
                  }}
                />
              }
              file={file}
              contextMenu={this.contextMenuUntracked}
              model={this.props.model}
              selected={this._isSelectedFile(file)}
              selectFile={this.updateSelectedFile}
            />
          );
        })}
      </GitStage>
    );
  }

  private _renderSimpleStage(files: Git.IStatusFile[]) {
    return (
      <GitStage
        actions={
          <ActionButton
            className={hiddenButtonStyle}
            disabled={files.length === 0}
            iconName={'git-discard'}
            title={'Discard All Changes'}
            onClick={this.discardAllChanges}
          />
        }
        heading={'Changed'}
        nFiles={files.length}
      >
        {files.map((file: Git.IStatusFile) => {
          let actions = null;
          if (file.status === 'unstaged') {
            actions = (
              <React.Fragment>
                <ActionButton
                  className={hiddenButtonStyle}
                  iconName={'git-discard'}
                  title={'Discard changes'}
                  onClick={() => {
                    this.discardChanges(file.to);
                  }}
                />
                {this._createDiffButton(file.to, 'WORKING')}
              </React.Fragment>
            );
          } else if (file.status === 'staged') {
            actions = this._createDiffButton(file.to, 'INDEX');
          }

          return (
            <FileItem
              key={file.to}
              actions={actions}
              file={file}
              markBox={true}
              model={this.props.model}
            />
          );
        })}
      </GitStage>
    );
  }

  /**
   * Creates a button element which is used to request diff of a file.
   *
   * @param path File path of interest
   * @param currentRef the ref to diff against the git 'HEAD' ref
   */
  private _createDiffButton(
    path: string,
    currentRef: ISpecialRef['specialRef']
  ): JSX.Element {
    return (
      isDiffSupported(path) && (
        <ActionButton
          className={hiddenButtonStyle}
          iconName={'git-diff'}
          title={'Diff this file'}
          onClick={async () => {
            try {
              await openDiffView(
                path,
                this.props.model,
                {
                  previousRef: { gitRef: 'HEAD' },
                  currentRef: { specialRef: currentRef }
                },
                this.props.renderMime
              );
            } catch (reason) {
              console.error(`Fail to open diff view for ${path}.\n${reason}`);
            }
          }}
        />
      )
    );
  }

  private _contextMenuStaged: Menu;
  private _contextMenuUnstaged: Menu;
  private _contextMenuUntracked: Menu;
}
