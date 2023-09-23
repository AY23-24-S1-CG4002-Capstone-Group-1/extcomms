using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class ShieldController : MonoBehaviour
{
    public TMP_Text shieldCountText;
    public Button shieldButton;

    private int shieldCount = 3; // Starting shields

    private void Start()
    {
        UpdateShieldText();

        shieldButton.onClick.AddListener(ActivateShield);
    }

    private void ActivateShield()
    {
        if (shieldCount > 0)
        {
            shieldCount--;
            UpdateShieldText();
        }

        // If shields run out, disable the shield button
        if (shieldCount <= 0)
        {
            shieldButton.interactable = false;
        }
    }

    private void UpdateShieldText()
    {
        shieldCountText.text = "x " + shieldCount;
    }

    public void ResetShields()
    {
        shieldCount = 3;
        UpdateShieldText();
        shieldButton.interactable = true;
    }

    public void SetShields(int x)
    {
        shieldCount = x;
        UpdateShieldText();
    }

}

