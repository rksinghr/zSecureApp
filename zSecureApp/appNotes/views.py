from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render

from .encryption import encrypt_text, decrypt_text
from .forms import ConfidentialNoteForm
from .models import ConfidentialNote, NoteRevision

@login_required
def note_view(request):
    # Only get the logged-in user's note
    note = ConfidentialNote.objects.filter(user=request.user).first()
    current_text = ""
    # Decrypt the current note for the owner
    if note:
        current_text = decrypt_text(note.ciphertext, note.nonce)
    # Handle form submission
    if request.method == "POST":
        form = ConfidentialNoteForm(request.POST)
        if form.is_valid():
            plaintext = form.cleaned_data["comment"]
            # Encrypt the new/updated note
            encrypted = encrypt_text(plaintext)
            with transaction.atomic():
                if note is None:
                    # First note for this user
                    note = ConfidentialNote.objects.create(user=request.user,
                        ciphertext=encrypted["ciphertext"], nonce=encrypted["nonce"])
                else:
                    # Update existing note
                    note.ciphertext = encrypted["ciphertext"]
                    note.nonce = encrypted["nonce"]
                    note.save(update_fields=["ciphertext", "nonce", "updated_at",])
                # Store encrypted revision
                NoteRevision.objects.create(note=note, ciphertext=encrypted["ciphertext"],
                    nonce=encrypted["nonce"], updated_by=request.user,)
            messages.success(request, "Your confidential information has been securely saved.")
            # Show the newly saved value in the form
            form = ConfidentialNoteForm(
                initial={
                    "comment": plaintext
                }
            )
            current_text = plaintext
    else:
        # GET request
        form = ConfidentialNoteForm(
            initial={
                "comment": current_text
            }
        )
    # Build revision history
    revisions = []

    if note:
        revision_queryset = (
            note.revisions
            .select_related("updated_by")
            .order_by("-created_at")
        )

        for revision in revision_queryset:
            revisions.append({
                "text": decrypt_text(
                    revision.ciphertext,
                    revision.nonce
                ),
                "date": revision.created_at,
                "updated_by": revision.updated_by,
            })

    return render(
        request,
        "appNotes/note.html",
        {
            "form": form,
            "note": note,
            "revisions": revisions,
        }
    )
