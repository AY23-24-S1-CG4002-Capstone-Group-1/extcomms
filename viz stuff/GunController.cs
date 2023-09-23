using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class GunController : MonoBehaviour
{
    public TMP_Text bulletCountText; // Now using TextMeshPro component
    public Button shootButton;
    public Button reloadButton;

    public int bulletCount = 6; // Starting bullets

    private void Start()
    {
        UpdateBulletText();

        shootButton.onClick.AddListener(Shoot);
        // reloadButton.onClick.AddListener(Reload);
    }

    private void Shoot()
    {
        if (bulletCount > 0)
        {
            bulletCount--;
            UpdateBulletText();
        }

        // If bullets run out, disable the shoot button
        if (bulletCount <= 0)
        {
            shootButton.interactable = false;
        }
    }

    public void Reload()
    {
        // Only reload if bullet count is 0
        if (bulletCount == 0)
        {
            bulletCount = 6;
            UpdateBulletText();
            shootButton.interactable = true; // Re-enable shoot button after reloading
        }
    }

    private void UpdateBulletText()
    {
        bulletCountText.text = bulletCount + " x";
    }

    public void ResetAmmo()
    {
        bulletCount = 6;
        UpdateBulletText();
        shootButton.interactable = true;
    }

    public void SetAmmo(int x)
    {
        bulletCount = x;
        UpdateBulletText();
    }

}
